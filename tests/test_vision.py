# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Image understanding.

The VisionAgent used to refuse every request twice over: once for having no
vision provider, and again for the model router being unable to send image
bytes even when one existed. Both are addressed here, and the two layers are
tested separately because they fail independently -- local analysis needs
Pillow, model description needs a provider and a network.

The line these tests hold hardest is that measurement is not recognition.
Local analysis can say an image is 1920x1080, mostly dark and almost
certainly a screenshot. It cannot say what the screenshot shows, and nothing
in the output may imply that it can.
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter

from aera.agents.base import Capability, Task
from aera.agents.media_agents import VisionAgent, _image_word
from aera.ai.base import AIProvider, CompletionRequest, ImageContent, Message, Role
from aera.api.app import create_app
from aera.core.errors import ValidationError
from aera.services import vision


@pytest.fixture(scope="module")
def images(tmp_path_factory) -> dict[str, str]:
    """Synthetic images with known, distinct characteristics.

    Generated rather than committed: a binary fixture nobody can inspect is
    a fixture nobody can reason about when the test fails.
    """
    import random

    directory = tmp_path_factory.mktemp("images")
    made: dict[str, str] = {}

    # Continuous tone, noisy, wide colour spread: a photograph.
    random.seed(7)
    photo = Image.new("RGB", (900, 600))
    pixels = photo.load()
    for y in range(600):
        for x in range(900):
            pixels[x, y] = (
                int(120 + 80 * random.random() + 40 * (x / 900)),
                int(90 + 70 * random.random() + 50 * (y / 600)),
                int(70 + 60 * random.random()),
            )
    photo.save(directory / "photo.jpg", quality=88)
    made["photo"] = str(directory / "photo.jpg")

    # Flat blocks of colour: a graphic.
    flat = Image.new("RGB", (1920, 1080), (24, 26, 33))
    draw = ImageDraw.Draw(flat)
    draw.rectangle([0, 0, 1920, 60], fill=(16, 18, 24))
    draw.rectangle([0, 60, 320, 1080], fill=(30, 33, 42))
    flat.save(directory / "flat.png")
    made["flat"] = str(directory / "flat.png")

    # Grey with heavy edge detail: a text-heavy interface.
    ui = Image.new("RGB", (1600, 1000), (250, 250, 252))
    pen = ImageDraw.Draw(ui)
    pen.rectangle([0, 0, 1600, 48], fill=(240, 240, 244))
    for row in range(30):
        for column in range(0, 1200, 7):
            pen.rectangle(
                [300 + column, 80 + row * 30, 302 + column, 90 + row * 30],
                fill=(40, 42, 52),
            )
    ui.save(directory / "ui.png")
    made["ui"] = str(directory / "ui.png")

    photo.filter(ImageFilter.GaussianBlur(9)).save(directory / "blurry.jpg", quality=88)
    made["blurry"] = str(directory / "blurry.jpg")

    Image.new("RGB", (800, 600), (8, 9, 12)).save(directory / "dark.png")
    made["dark"] = str(directory / "dark.png")

    Image.new("RGB", (40, 40), (200, 30, 30)).save(directory / "tiny.png")
    made["tiny"] = str(directory / "tiny.png")

    Image.new("RGB", (4000, 2500), (90, 140, 200)).save(directory / "huge.jpg", quality=85)
    made["huge"] = str(directory / "huge.jpg")

    (directory / "notanimage.txt").write_text("hello")
    made["text"] = str(directory / "notanimage.txt")

    return made


class TestMeasurement:
    def test_reads_dimensions_and_format(self, images):
        analysis = vision.analyse(images["photo"])

        assert (analysis.width, analysis.height) == (900, 600)
        assert analysis.fmt == "JPEG"
        assert analysis.megapixels == pytest.approx(0.54, abs=0.01)

    @pytest.mark.parametrize(
        ("key", "orientation", "aspect"),
        [("photo", "landscape", "3:2"), ("flat", "landscape", "16:9"), ("tiny", "square", "square")],
    )
    def test_orientation_and_aspect(self, images, key, orientation, aspect):
        analysis = vision.analyse(images[key])

        assert analysis.orientation == orientation
        assert analysis.aspect == aspect

    def test_brightness_separates_dark_from_light(self, images):
        assert vision.analyse(images["dark"]).brightness < 0.15
        assert vision.analyse(images["ui"]).brightness > 0.6

    def test_sharpness_detects_blur(self, images):
        """The same image, blurred, must measure softer."""
        sharp = vision.analyse(images["photo"]).sharpness
        soft = vision.analyse(images["blurry"]).sharpness

        assert soft < sharp

    def test_a_palette_is_extracted(self, images):
        colours = vision.analyse(images["photo"]).colours

        assert colours
        assert all(c.hex.startswith("#") and len(c.hex) == 7 for c in colours)
        assert all(0.0 <= c.weight <= 1.0 for c in colours)

    def test_colours_are_ranked_by_share(self, images):
        weights = [c.weight for c in vision.analyse(images["photo"]).colours]

        assert weights == sorted(weights, reverse=True)


class TestColourNaming:
    @pytest.mark.parametrize(
        ("rgb", "name"),
        [
            ((255, 0, 0), "red"), ((0, 200, 0), "green"), ((0, 0, 220), "blue"),
            ((255, 165, 0), "orange"), ((250, 250, 250), "white"),
            ((10, 10, 10), "black"), ((128, 128, 128), "grey"),
        ],
    )
    def test_names_a_colour_the_way_a_person_would(self, rgb, name):
        assert vision.colour_name(rgb) == name

    def test_a_desaturated_colour_is_grey_not_a_hue(self):
        """#333333 has a hue. Calling it green because that hue rounds into
        the green range is worse than useless."""
        assert "green" not in vision.colour_name((51, 52, 51))
        assert "grey" in vision.colour_name((51, 52, 51))


class TestClassification:
    """Photograph, screenshot, graphic or scan.

    Flatness -- the share of the frame held by the three commonest colour
    bins -- is the primary signal, and it was completely broken at first:
    the palette was merged by colour name *before* flatness was computed, so
    every image collapsed to 1.00 and every photograph was classified as a
    screenshot.
    """

    def test_a_photograph_is_recognised(self, images):
        assert vision.analyse(images["photo"]).kind == "photograph"

    def test_a_flat_graphic_is_not_called_a_photograph(self, images):
        assert vision.analyse(images["flat"]).kind != "photograph"

    def test_a_text_heavy_interface_is_recognised(self, images):
        """Glyph edges spread the histogram, so flatness alone reads this as
        a photograph -- 0.28 on a realistic mock. Near-zero saturation with
        very high edge energy is what actually gives it away."""
        assert "screenshot" in vision.analyse(images["ui"]).kind

    def test_flatness_actually_discriminates(self, images):
        """The regression guard: these must not be equal."""
        photo = vision.analyse(images["photo"]).flatness
        flat = vision.analyse(images["flat"]).flatness

        assert photo < 0.3
        assert flat > 0.6

    def test_the_analysis_never_claims_to_identify_objects(self, images):
        for key in ("photo", "flat", "ui", "dark"):
            assert vision.analyse(images[key]).to_dict()["identifies_objects"] is False


class TestQualityNotes:
    def test_blur_is_reported(self, images):
        notes = " ".join(vision.analyse(images["blurry"]).quality_notes)

        assert "soft" in notes or "focus" in notes

    def test_darkness_is_reported(self, images):
        assert any("dark" in n for n in vision.analyse(images["dark"]).quality_notes)

    def test_a_small_image_is_flagged(self, images):
        notes = vision.analyse(images["tiny"]).quality_notes

        assert any("low-resolution" in n or "small" in n for n in notes)

    def test_a_good_image_has_nothing_to_complain_about(self, images):
        assert vision.analyse(images["photo"]).quality_notes == []


class TestDescription:
    def test_it_reads_as_a_sentence(self, images):
        text = vision.analyse(images["photo"]).describe()

        assert text.endswith(".")
        assert "900x600" in text

    def test_it_states_what_it_measured_not_what_it_saw(self, images):
        """No verb of recognition may appear: this layer sees no objects."""
        text = vision.analyse(images["photo"]).describe().lower()

        for claim in ("i can see", "contains a", "shows a person", "depicts"):
            assert claim not in text


class TestErrors:
    def test_a_missing_file_is_named(self):
        with pytest.raises(ValidationError, match="no such image"):
            vision.analyse("/tmp/definitely-not-here.png")

    def test_an_unsupported_format_lists_what_is_supported(self, images):
        with pytest.raises(ValidationError, match="unsupported image format"):
            vision.analyse(images["text"])


class TestTransport:
    """Preparing an image for a provider."""

    def test_it_encodes_to_base64(self, images):
        payload = vision.prepare(images["photo"])

        assert payload.data
        assert payload.media_type == "image/jpeg"
        assert payload.to_data_url().startswith("data:image/jpeg;base64,")

    def test_a_large_image_is_downsampled(self, images):
        """Providers resize server-side anyway; sending 4000 px wastes time
        and tokens for no gain in what is recognised."""
        payload = vision.prepare(images["huge"])

        assert payload.resized is True
        assert max(payload.width, payload.height) <= vision.MAX_EDGE_PX

    def test_a_small_image_is_sent_untouched(self, images):
        assert vision.prepare(images["photo"]).resized is False

    def test_tokens_are_estimated(self, images):
        small = vision.estimate_tokens(vision.prepare(images["tiny"]))
        large = vision.estimate_tokens(vision.prepare(images["huge"]))

        assert 0 < small < large


class TestWireFormats:
    """Each provider spells the image payload differently.

    Getting one of these wrong produces a 400 from the provider, which is
    exactly the kind of failure that only shows up against a live key.
    """

    @pytest.fixture
    def message(self) -> Message:
        return Message(
            role=Role.USER,
            content="what is this?",
            images=[ImageContent(data="QUJD", media_type="image/png")],
        )

    def test_openai_uses_a_data_url(self, message):
        wire = message.to_wire()
        parts = wire["content"]

        assert parts[0] == {"type": "text", "text": "what is this?"}
        assert parts[1]["type"] == "image_url"
        assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")

    def test_anthropic_nests_under_source_with_media_type(self, message):
        from aera.ai.providers.anthropic import AnthropicProvider

        blocks = AnthropicProvider._content(message)

        assert blocks[1]["type"] == "image"
        assert blocks[1]["source"]["media_type"] == "image/png"
        assert blocks[1]["source"]["data"] == "QUJD"

    def test_gemini_spells_it_mime_type(self, message):
        """Not media_type. A single character, and the request fails."""
        from aera.ai.providers.gemini import GeminiProvider

        parts = GeminiProvider._parts(message)

        assert parts[1]["inline_data"]["mime_type"] == "image/png"
        assert parts[1]["inline_data"]["data"] == "QUJD"

    def test_a_text_only_message_keeps_the_plain_string_form(self):
        """The content list is only valid on multimodal endpoints. Sending it
        unconditionally breaks deployments that accept a string and nothing
        else -- which is every older one."""
        from aera.ai.providers.anthropic import AnthropicProvider

        plain = Message(role=Role.USER, content="hello")

        assert plain.to_wire()["content"] == "hello"
        assert AnthropicProvider._content(plain) == "hello"

    def test_a_request_carrying_an_image_is_valid(self, message):
        request = CompletionRequest(messages=[message])

        assert request.messages[0].has_images


class TestVisionAgent:
    async def test_it_analyses_without_any_model(self, agent_context, images):
        """The point of the local layer: no provider, still useful."""
        agent = VisionAgent(agent_context)

        result = await agent.handle(
            Task(capability=Capability.VISION, input=f"describe {images['photo']}")
        )

        assert result.success is True
        assert result.data["analysis"]["width"] == 900

    async def test_it_says_when_no_model_described_it(self, agent_context, images):
        agent = VisionAgent(agent_context)

        result = await agent.handle(
            Task(capability=Capability.VISION, input=f"describe {images['photo']}")
        )

        assert result.data["described_by_model"] is False
        assert "no vision-capable model" in result.output.lower()

    async def test_a_missing_image_fails_clearly(self, agent_context):
        agent = VisionAgent(agent_context)

        result = await agent.handle(
            Task(capability=Capability.VISION, input="describe /tmp/nope.png")
        )

        assert result.success is False
        assert "could not read" in result.output

    async def test_no_image_at_all_asks_for_one(self, agent_context):
        agent = VisionAgent(agent_context)

        result = await agent.handle(Task(capability=Capability.VISION, input="hello"))

        assert result.success is False
        assert ".png" in result.output

    async def test_the_path_can_come_from_context(self, agent_context, images):
        agent = VisionAgent(agent_context)

        result = await agent.handle(
            Task(capability=Capability.VISION, input="what is this?",
                 context={"path": images["flat"]})
        )

        assert result.success is True

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("describe assets/brand/banner.png", "assets/brand/banner.png"),
            ("what is in photo.jpg", "photo.jpg"),
            ("no image here", None),
            ("a file.txt", None),
        ],
    )
    def test_a_relative_filename_is_recognised(self, text, expected):
        """_PATH_RE requires a leading / or ~ and several agents rely on that,
        so vision handles the bare-filename case itself."""
        assert _image_word(text) == expected


class FakeVisionProvider(AIProvider):
    """A provider that can see, so the multimodal path can be exercised.

    Records what it was handed. Without this the transport is only tested
    at the serialisation layer, and "the bytes reach a provider" stays an
    assumption -- which is exactly where the real bugs were.
    """

    name = "fakevision"

    def __init__(self) -> None:
        super().__init__()
        self.received: dict[str, object] = {}

    async def complete(self, request):
        from aera.ai.base import CompletionResponse, Usage

        message = request.messages[-1]
        self.received = {
            "images": len(message.images),
            "bytes": len(base64.b64decode(message.images[0].data)) if message.images else 0,
            "media_type": message.images[0].media_type if message.images else None,
            "question": message.content,
            "model": request.model,
        }
        return CompletionResponse(
            content="A warm orange gradient with no clear subject.",
            model="fake-v",
            provider=self.name,
            usage=Usage(),
        )

    async def list_models(self):
        from aera.ai.base import ModelInfo

        return [ModelInfo(id="fake-v", name="fake-v", provider=self.name, supports_vision=True)]

    async def stream(self, request):
        yield "x"

    async def embed(self, texts):
        return [[0.0] for _ in texts]

    async def _probe(self) -> bool:
        return True


class TestMultimodalDelivery:
    """The image bytes actually reach a vision provider.

    This is what the agent could not do before: it reported "multimodal
    transport is the remaining piece" and stopped. Three separate bugs sat
    on this path -- the router was called with a CompletionRequest when it
    takes a message list, the preference chain handed the request to a
    text-only local model that answered from the filename, and the response
    was discarded.
    """

    @pytest.fixture
    async def kernel_with_vision(self, kernel):
        provider = FakeVisionProvider()
        kernel.router.register(provider)
        return kernel, provider

    async def test_the_provider_receives_the_image(self, kernel_with_vision, images):
        kernel, provider = kernel_with_vision

        await kernel.registry.agents["vision"].handle(
            Task(capability=Capability.VISION, input=f"what is in {images['photo']}")
        )

        assert provider.received["images"] == 1
        assert provider.received["bytes"] > 10_000
        assert provider.received["media_type"] == "image/jpeg"

    async def test_the_model_answer_is_returned(self, kernel_with_vision, images):
        kernel, _ = kernel_with_vision

        result = await kernel.registry.agents["vision"].handle(
            Task(capability=Capability.VISION, input=f"what is in {images['photo']}")
        )

        assert result.data["described_by_model"] is True
        assert "orange gradient" in result.output

    async def test_a_text_only_model_does_not_answer_instead(
        self, kernel_with_vision, images
    ):
        """Under local_first the chain prefers a local text model, which
        would answer from the filename having never seen the image. Failing
        over to something that cannot see is worse than not answering."""
        kernel, _ = kernel_with_vision

        result = await kernel.registry.agents["vision"].handle(
            Task(capability=Capability.VISION, input=f"what is in {images['photo']}")
        )

        assert "built-in offline reasoner" not in result.output
        assert result.data["provider"] == "fakevision"

    async def test_the_question_is_passed_through(self, kernel_with_vision, images):
        kernel, provider = kernel_with_vision

        await kernel.registry.agents["vision"].handle(
            Task(capability=Capability.VISION, input="how many people are here?",
                 context={"path": images["photo"]})
        )

        assert provider.received["question"] == "how many people are here?"

    async def test_what_was_sent_is_reported(self, kernel_with_vision, images):
        """A caller should be able to see the size and cost of what went out."""
        kernel, _ = kernel_with_vision

        result = await kernel.registry.agents["vision"].handle(
            Task(capability=Capability.VISION, input=f"describe {images['photo']}")
        )

        assert result.data["image_sent"]["bytes_sent"] > 0
        assert result.data["estimated_tokens"] > 0

    async def test_a_failing_provider_falls_back_to_measurement(
        self, kernel_with_vision, images, monkeypatch
    ):
        """A provider error must not lose the analysis that already worked."""
        kernel, provider = kernel_with_vision

        async def boom(_request):
            raise RuntimeError("provider exploded")

        monkeypatch.setattr(provider, "complete", boom)
        result = await kernel.registry.agents["vision"].handle(
            Task(capability=Capability.VISION, input=f"describe {images['photo']}")
        )

        assert result.success is True
        assert result.data["described_by_model"] is False
        assert result.data["analysis"]["width"] == 900


class TestVisionApi:
    @pytest.fixture
    def client(self, config):
        with TestClient(create_app(config)) as c:
            yield c

    def test_status_reports_both_layers_separately(self, client):
        """They fail independently: Pillow for one, a provider for the other."""
        data = client.get("/api/v1/vision/status").json()["data"]

        assert data["local_analysis"] is True
        assert data["model_description"] is False
        assert data["local_identifies_objects"] is False

    def test_analyse_returns_measurements(self, client, images):
        data = client.post(
            "/api/v1/vision/analyse", json={"path": images["ui"]}
        ).json()["data"]

        assert data["width"] == 1600
        assert "screenshot" in data["kind"]
        assert data["colours"]

    def test_analyse_without_a_path_is_refused(self, client):
        assert client.post("/api/v1/vision/analyse", json={}).status_code == 400

    def test_analyse_of_a_missing_file_is_refused(self, client):
        response = client.post("/api/v1/vision/analyse", json={"path": "/tmp/nope.png"})

        assert response.status_code == 400
        assert "no such image" in response.json()["error"]

    def test_estimate_reports_size_and_tokens(self, client, images):
        data = client.post(
            "/api/v1/vision/estimate", json={"path": images["photo"]}
        ).json()["data"]

        assert data["bytes_sent"] > 0
        assert data["estimated_tokens"] > 0
        assert "approximation" in data["note"]

    def test_describe_falls_back_to_measurement(self, client, images):
        """With no vision model configured this must still succeed, and must
        say that nothing identified the contents."""
        data = client.post(
            "/api/v1/vision/describe", json={"path": images["photo"]}
        ).json()["data"]

        assert data["success"] is True
        assert data["data"]["described_by_model"] is False
