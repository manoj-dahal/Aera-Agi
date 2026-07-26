# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Tests for the document, media, network and conversation agents.

These agents are capability-gated: when a backend is absent they must say so
precisely rather than fabricating a result. That honesty is the contract under
test here.
"""

from __future__ import annotations

import pytest

from aera.agents import Task
from aera.agents.media_agents import (
    AudioAgent,
    CollaborationAgent,
    ConversationAgent,
    DocumentAgent,
    NetworkAgent,
    OCRAgent,
    PersonalizationAgent,
    VisionAgent,
    VoiceAgent,
    WebAgent,
    _is_private_url,
    _strip_html,
)


async def run(agent_cls, context, text: str, **ctx):
    agent = agent_cls(context)
    await agent.start()
    task = Task(input=text)
    task.context.update(ctx)
    return await agent.execute(task)


class TestDocumentAgent:
    async def test_reads_a_text_file(self, agent_context, tmp_path):
        doc = tmp_path / "notes.md"
        doc.write_text("# Deployment\n\nRun docker compose up.\n")
        result = await run(DocumentAgent, agent_context, "summarise it", path=str(doc))
        assert result.success
        assert result.data["source"].endswith("notes.md")
        assert result.data["characters"] > 0

    async def test_missing_file_reports_clearly(self, agent_context):
        result = await run(DocumentAgent, agent_context, "read /no/such/file.txt")
        assert result.success is False
        assert "not found" in (result.error or "")

    async def test_binary_format_is_refused_not_guessed(self, agent_context, tmp_path):
        pdf = tmp_path / "report.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        result = await run(DocumentAgent, agent_context, "summarise", path=str(pdf))
        assert result.success is False
        assert result.data["parser_available"] is False
        assert "PDF" in result.output

    async def test_inline_text_when_no_path(self, agent_context):
        result = await run(DocumentAgent, agent_context, "Summarise: AERA is an AI OS.")
        assert result.success and result.data["source"] == "inline text"

    async def test_large_file_is_truncated(self, agent_context, tmp_path):
        big = tmp_path / "big.txt"
        big.write_text("word " * 20_000)
        result = await run(DocumentAgent, agent_context, "summarise", path=str(big))
        assert result.data["truncated"] is True


class TestCapabilityGating:
    """Agents without a backend must fail honestly."""

    async def test_vision_reports_a_missing_file(self, agent_context):
        """Vision no longer refuses outright when no model is connected: it
        measures the image locally and says nothing identified the contents.
        So a nonexistent path now fails on the file, which is the honest
        reason, rather than on the absent provider."""
        result = await run(VisionAgent, agent_context, "describe /tmp/shot.png")

        assert result.success is False
        assert "could not read" in result.output

    async def test_vision_analyses_locally_without_a_model(self, agent_context, tmp_path):
        """The capability that replaced the refusal. See tests/test_vision.py
        for the full behaviour."""
        from PIL import Image

        image = tmp_path / "x.png"
        Image.new("RGB", (320, 240), (12, 90, 200)).save(image)

        result = await run(VisionAgent, agent_context, f"describe {image}")

        assert result.success is True
        assert result.data["analysis"]["width"] == 320
        assert result.data["described_by_model"] is False

    async def test_ocr_reports_missing_engine(self, agent_context):
        result = await run(OCRAgent, agent_context, "extract text from /tmp/scan.png")
        assert result.success is False
        assert result.data["engine"] is None
        assert "OCR" in result.output

    async def test_audio_reports_missing_stt(self, agent_context):
        result = await run(AudioAgent, agent_context, "transcribe /tmp/clip.wav")
        assert result.success is False
        assert "speech-to-text" in result.output

    async def test_gated_agents_never_invent_content(self, agent_context):
        """The failure text must not read like a real analysis."""
        for agent_cls, prompt in (
            (VisionAgent, "what is in /tmp/a.png"),
            (OCRAgent, "read /tmp/a.png"),
            (AudioAgent, "transcribe /tmp/a.wav"),
        ):
            result = await run(agent_cls, agent_context, prompt)
            assert result.success is False
            assert result.error


class TestNetworkAgent:
    async def test_reports_host_status(self, agent_context):
        result = await run(NetworkAgent, agent_context, "network status")
        assert result.success and "hostname" in result.data

    async def test_resolves_a_name(self, agent_context):
        result = await run(
            NetworkAgent, agent_context, "resolve localhost",
            action="resolve", host="localhost",
        )
        assert result.success and result.data["addresses"]

    async def test_unresolvable_name_fails_cleanly(self, agent_context):
        result = await run(
            NetworkAgent, agent_context, "resolve x",
            action="resolve", host="nonexistent.invalid.",
        )
        assert result.success is False


class TestWebAgentSafety:
    async def test_disabled_by_policy_by_default(self, agent_context):
        result = await run(WebAgent, agent_context, "fetch https://example.com")
        assert result.success is False
        assert "disabled" in result.output

    async def test_requires_a_url(self, agent_context):
        result = await run(WebAgent, agent_context, "fetch something")
        assert result.success is False

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8080/admin",
            "http://localhost/secret",
            "http://192.168.1.1/",
            "http://10.0.0.5/",
            "http://169.254.169.254/latest/meta-data",
        ],
    )
    async def test_refuses_private_addresses(self, agent_context, config, url):
        """SSRF guard: a prompt must not be able to probe the internal network."""
        config.security.allow_network = True
        result = await run(WebAgent, agent_context, f"fetch {url}")
        assert result.success is False
        assert "private" in (result.error or "") or "refus" in result.output.lower()

    def test_private_url_detection(self):
        assert _is_private_url("http://127.0.0.1/") is True
        assert _is_private_url("http://localhost/") is True
        assert _is_private_url("not-a-url") is True  # fail closed

    def test_html_stripping(self):
        html = "<html><script>bad()</script><p>Hello <b>world</b></p></html>"
        text = _strip_html(html)
        assert "bad()" not in text and "Hello world" in text


class TestConversationAndPersonalization:
    async def test_conversation_replies(self, agent_context):
        result = await run(ConversationAgent, agent_context, "hello there")
        assert result.success and result.output

    async def test_personalization_learns_a_preference(self, agent_context):
        result = await run(PersonalizationAgent, agent_context, "I prefer dark mode")
        assert result.success and result.data["stored"] is True
        assert result.memory_ids

    async def test_personalization_lists_preferences(self, agent_context):
        await run(PersonalizationAgent, agent_context, "I always use tabs")
        result = await run(PersonalizationAgent, agent_context, "what do you know", action="list")
        assert result.success and result.data["preferences"]

    async def test_personalization_empty_state(self, agent_context):
        result = await run(PersonalizationAgent, agent_context, "show me", action="list")
        assert result.success and "not learned any" in result.output


class TestCollaborationAndVoice:
    async def test_collaboration_plans_a_handoff(self, registry, agent_context):
        agent_context.registry = registry
        result = await run(CollaborationAgent, agent_context, "ship a new feature")
        assert result.success and result.data["agents_available"] > 0

    async def test_voice_agent_speaks(self, agent_context, config, bus):
        from aera.voice.engine import VoiceEngine

        agent_context.voice = VoiceEngine(config.voice, bus=bus)
        result = await run(VoiceAgent, agent_context, "This is excellent news!")
        assert result.success and result.data["duration_ms"] > 0

    async def test_voice_agent_detects_emotion(self, agent_context, config, bus):
        from aera.voice.engine import VoiceEngine

        agent_context.voice = VoiceEngine(config.voice, bus=bus)
        result = await run(
            VoiceAgent, agent_context, "critical security failure", action="emotion"
        )
        assert result.success and result.data["emotion"] == "serious"


class TestFullRoster:
    """The conversation lists 31 agents; every one must be registered."""

    ROSTER = [
        "core", "memory", "voice", "conversation", "planning", "reasoning",
        "coding", "debug", "terminal", "research", "web", "vision", "audio",
        "document", "ocr", "translation", "writing", "workspace", "automation",
        "device", "security", "network", "monitoring", "performance", "backup",
        "update", "notification", "scheduler", "learning", "personalization",
        "collaboration", "ethical_hacking",
    ]

    def test_every_agent_is_available(self, agent_context, config):
        from aera.agents import build_default_registry

        # Enable the opt-in agents so the full roster is present.
        config.agents.audio = True
        config.agents.web = True
        config.agents.terminal = True
        registry = build_default_registry(agent_context, config.agents)

        missing = [name for name in self.ROSTER if name not in registry.names()]
        assert not missing, f"agents missing from the roster: {missing}"

    def test_risky_agents_are_off_by_default(self, agent_context, config):
        from aera.agents import build_default_registry

        registry = build_default_registry(agent_context, config.agents)
        # Terminal executes shell commands; web makes outbound requests.
        assert "terminal" not in registry.names()
        assert "web" not in registry.names()


class TestAudioTranscription:
    """AudioAgent with a live STT backend.

    A regression suite: the agent used to return success=True with the text
    "Transcription would run through the '<name>' backend" whenever a backend
    was registered -- reporting success while doing no work, which is exactly
    the fabrication these agents exist to avoid. Nothing caught it because
    every test ran against the null backend.
    """

    @staticmethod
    def _wav(path):
        import struct
        import wave

        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16_000)
            handle.writeframes(struct.pack("<h", 0) * 1600)
        return path

    @staticmethod
    def _context(agent_context, stt):
        from aera.voice.engine import VoiceEngine

        agent_context.voice = VoiceEngine(stt=stt)
        return agent_context

    async def test_transcribes_through_the_backend(self, agent_context, tmp_path, stt_factory):
        clip = self._wav(tmp_path / "clip.wav")
        context = self._context(agent_context, stt_factory("hello world"))

        result = await run(AudioAgent, context, f"transcribe {clip}")

        assert result.success is True
        assert result.output == "hello world"
        assert result.data["characters"] == len("hello world")
        assert result.data["stt_backend"] == "fake-stt"

    async def test_passes_the_audio_bytes_to_the_backend(
        self, agent_context, tmp_path, stt_factory
    ):
        """The file must actually be read, not just named."""
        clip = self._wav(tmp_path / "clip.wav")
        stt = stt_factory("ok")
        context = self._context(agent_context, stt)

        await run(AudioAgent, context, f"transcribe {clip}")

        assert stt.received == clip.read_bytes()

    async def test_forwards_the_requested_language(self, agent_context, tmp_path, stt_factory):
        clip = self._wav(tmp_path / "clip.wav")
        stt = stt_factory("bonjour")
        context = self._context(agent_context, stt)

        await run(AudioAgent, context, f"transcribe {clip}", language="fr")

        assert stt.language == "fr"

    async def test_reports_metadata_from_the_transcript(
        self, agent_context, tmp_path, stt_factory
    ):
        clip = self._wav(tmp_path / "clip.wav")
        context = self._context(agent_context, stt_factory("hi"))

        result = await run(AudioAgent, context, f"transcribe {clip}")

        assert result.data["confidence"] == 0.97
        assert result.data["duration_ms"] == 1200.0

    async def test_silence_is_not_a_success(self, agent_context, tmp_path, stt_factory):
        """An empty transcript is a real outcome but not a successful read."""
        clip = self._wav(tmp_path / "clip.wav")
        context = self._context(agent_context, stt_factory(""))

        result = await run(AudioAgent, context, f"transcribe {clip}")

        assert result.success is False
        assert "No speech" in result.output

    async def test_backend_failure_is_surfaced(self, agent_context, tmp_path, stt_factory):
        clip = self._wav(tmp_path / "clip.wav")
        context = self._context(agent_context, stt_factory(RuntimeError("model corrupt")))

        result = await run(AudioAgent, context, f"transcribe {clip}")

        assert result.success is False
        assert "model corrupt" in result.error

    async def test_missing_file_is_reported(self, agent_context, tmp_path, stt_factory):
        context = self._context(agent_context, stt_factory("x"))

        result = await run(AudioAgent, context, f"transcribe {tmp_path / 'absent.wav'}")

        assert result.success is False
        assert "not found" in result.error

    async def test_requires_a_path(self, agent_context, stt_factory):
        context = self._context(agent_context, stt_factory("x"))

        result = await run(AudioAgent, context, "transcribe the recording")

        assert result.success is False
        assert result.error == "no audio path given"

    async def test_oversized_audio_is_refused(
        self, agent_context, tmp_path, stt_factory, monkeypatch
    ):
        """Whole-file reads must not be able to exhaust memory."""
        clip = self._wav(tmp_path / "clip.wav")
        context = self._context(agent_context, stt_factory("x"))
        monkeypatch.setattr(AudioAgent, "MAX_BYTES", 10)

        result = await run(AudioAgent, context, f"transcribe {clip}")

        assert result.success is False
        assert result.error == "audio file too large"

    async def test_never_claims_success_without_transcribing(
        self, agent_context, tmp_path, stt_factory
    ):
        """The exact regression: success implies real output from the backend."""
        clip = self._wav(tmp_path / "clip.wav")
        context = self._context(agent_context, stt_factory("actual words"))

        result = await run(AudioAgent, context, f"transcribe {clip}")

        assert "would run" not in result.output
        assert result.success is (result.output == "actual words")
