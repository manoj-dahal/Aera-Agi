# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Image understanding.

Two layers, because they answer different questions and fail differently.

**Local analysis** reads the pixels: dimensions, orientation, dominant
colours, brightness, contrast, sharpness, whether the image is a photograph
or a screenshot, whether it looks like a chart or a document scan. This runs
offline with no model, always returns something true, and is what makes the
rest of AERA's offline-first promise hold for images.

**Model description** sends the image to a vision-capable provider and asks
what is in it. That needs a provider, a network and a multimodal request
shape. When one is missing this layer says so rather than substituting a
guess -- a caption invented from colour statistics would be worse than
silence, because it would read like understanding.

What local analysis honestly cannot do is name objects. It can say an image
is 1920x1080, mostly dark, low saturation, sharp, and almost certainly a
screenshot rather than a photograph. It cannot say it is a screenshot *of a
terminal*. That boundary is stated in the output rather than left for a
reader to discover, because measurements dressed up as description are the
main way a vision feature lies.
"""

from __future__ import annotations

import base64
import colorsys
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.errors import ValidationError
from ..core.logging import get_logger

logger = get_logger("services.vision")

#: Formats Pillow reads that a provider will also accept. Anything else is
#: refused by name rather than failing deep inside the decoder.
SUPPORTED_FORMATS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})

#: Providers reject very large payloads and base64 inflates by a third.
#: 20 MB is the smallest common ceiling across OpenAI, Anthropic and Gemini.
MAX_IMAGE_BYTES = 20 * 1024 * 1024

#: Longest edge to send. Every provider downsamples anyway, and shipping a
#: 6000 px photo wastes tokens and time for no gain in what is recognised.
MAX_EDGE_PX = 1568

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
}


def pillow_available() -> bool:
    """Whether local analysis can run at all."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass(frozen=True)
class Colour:
    """One dominant colour, with a name a person would use."""

    rgb: tuple[int, int, int]
    #: Share of the image, 0..1.
    weight: float
    name: str

    @property
    def hex(self) -> str:
        return "#{:02x}{:02x}{:02x}".format(*self.rgb)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hex": self.hex,
            "rgb": list(self.rgb),
            "name": self.name,
            "weight": round(self.weight, 3),
        }


#: Hue ranges in degrees, with the name each maps to. Ordered so a lookup
#: takes the first match.
_HUE_NAMES: tuple[tuple[float, float, str], ...] = (
    (0, 15, "red"), (15, 45, "orange"), (45, 70, "yellow"),
    (70, 160, "green"), (160, 200, "cyan"), (200, 250, "blue"),
    (250, 290, "purple"), (290, 335, "magenta"), (335, 360, "red"),
)


def colour_name(rgb: tuple[int, int, int]) -> str:
    """A plain-language name for a colour.

    Greys are named before hue is considered: a nearly desaturated pixel has
    a hue, but calling #333333 "green" because its hue rounds into that range
    is worse than useless.
    """
    red, green, blue = (channel / 255.0 for channel in rgb)
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)

    if saturation < 0.12:
        if lightness < 0.15:
            return "black"
        if lightness < 0.4:
            return "dark grey"
        if lightness < 0.7:
            return "grey"
        if lightness < 0.92:
            return "light grey"
        return "white"

    degrees = hue * 360.0
    base = next((name for low, high, name in _HUE_NAMES if low <= degrees < high), "grey")
    if lightness < 0.25:
        return f"dark {base}"
    if lightness > 0.78:
        return f"pale {base}"
    return base


@dataclass
class ImageAnalysis:
    """What can be measured from an image without a model."""

    path: str
    width: int
    height: int
    fmt: str
    size_bytes: int
    mode: str
    colours: list[Colour] = field(default_factory=list)
    #: 0..1 mean luminance.
    brightness: float = 0.0
    #: 0..1 spread of luminance. Low means flat, high means punchy.
    contrast: float = 0.0
    #: 0..1 mean saturation.
    saturation: float = 0.0
    #: Edge energy. Low suggests blur or a very plain image.
    sharpness: float = 0.0
    #: How few distinct colours dominate. Screenshots and charts are flat.
    flatness: float = 0.0
    has_alpha: bool = False
    animated: bool = False

    @property
    def megapixels(self) -> float:
        return round(self.width * self.height / 1_000_000, 2)

    @property
    def aspect(self) -> str:
        """A named aspect ratio, which is more useful than a decimal."""
        if not self.height:
            return "unknown"
        ratio = self.width / self.height
        for value, name in (
            (1.0, "square"), (4 / 3, "4:3"), (3 / 2, "3:2"),
            (16 / 10, "16:10"), (16 / 9, "16:9"), (21 / 9, "21:9"),
        ):
            if abs(ratio - value) < 0.04:
                return name
        return "portrait" if ratio < 1 else "landscape"

    @property
    def orientation(self) -> str:
        if self.width == self.height:
            return "square"
        return "landscape" if self.width > self.height else "portrait"

    @property
    def kind(self) -> str:
        """Photograph, screenshot, graphic or scan -- inferred, and only
        this far.

        Two signals, because neither alone is sufficient. Flatness --
        the share of the frame taken by the three commonest colour bins --
        separates synthetic images from continuous-tone ones: a screenshot
        scores around 0.8, a photograph around 0.12. But a text-heavy
        interface breaks that, because thousands of glyph edges spread the
        histogram; measured 0.28 on a realistic UI mock, which read as a
        photograph on flatness alone. Such an image is instead betrayed by
        near-zero saturation with very high edge energy, which no photograph
        produces.

        This says nothing about *what* is depicted, which is the limit of
        what pixels support without a model.
        """
        if self.animated:
            return "animation"
        # Rendered text and chrome: grey, and full of hard edges.
        if self.saturation < 0.12 and self.sharpness > 0.35:
            return "screenshot or user interface"
        if self.flatness > 0.55:
            return (
                "screenshot or user interface"
                if self.sharpness > 0.06
                else "graphic or illustration"
            )
        if self.saturation < 0.08 and self.contrast > 0.22:
            return "document scan or line art"
        return "photograph"

    @property
    def quality_notes(self) -> list[str]:
        """Problems worth mentioning before anyone builds on this image."""
        notes: list[str] = []
        # Measured against known images: a sharp photograph scores ~0.23 and
        # the same photograph under a 9-pixel blur scores ~0.05. A 0.02
        # threshold sat below both and never fired.
        if self.sharpness < 0.08:
            notes.append("very soft: likely out of focus or heavily compressed")
        if self.brightness < 0.12:
            notes.append("very dark: detail in shadows is probably lost")
        elif self.brightness > 0.9:
            notes.append("very bright: highlights are probably clipped")
        # Contrast here is the standard deviation of luminance over a
        # thumbnail, which is small even for good images -- a normal noisy
        # photograph measures ~0.04, so 0.06 flagged healthy pictures as
        # defective. Only genuinely uniform frames should be called flat.
        if self.contrast < 0.02:
            notes.append("flat contrast: little tonal separation")
        if self.width < 200 or self.height < 200:
            notes.append("small: too low-resolution for reliable recognition")
        return notes

    def describe(self) -> str:
        """A sentence a person can read, saying only what was measured."""
        palette = ", ".join(c.name for c in self.colours[:3]) or "no dominant colour"
        lit = (
            "dark" if self.brightness < 0.3
            else "bright" if self.brightness > 0.7
            else "mid-toned"
        )
        parts = [
            f"A {self.width}x{self.height} {self.fmt} image ({self.megapixels} MP, "
            f"{self.orientation}, {self.aspect}).",
            f"It appears to be a {self.kind}.",
            f"The palette is mostly {palette}, and the image is {lit}.",
        ]
        if self.quality_notes:
            parts.append("Note: " + "; ".join(self.quality_notes) + ".")
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "megapixels": self.megapixels,
            "format": self.fmt,
            "mode": self.mode,
            "size_bytes": self.size_bytes,
            "orientation": self.orientation,
            "aspect": self.aspect,
            "kind": self.kind,
            "colours": [c.to_dict() for c in self.colours],
            "brightness": round(self.brightness, 3),
            "contrast": round(self.contrast, 3),
            "saturation": round(self.saturation, 3),
            "sharpness": round(self.sharpness, 3),
            "flatness": round(self.flatness, 3),
            "has_alpha": self.has_alpha,
            "animated": self.animated,
            "quality_notes": self.quality_notes,
            "description": self.describe(),
            # Said in the payload, not only in the prose: this is measurement,
            # not recognition.
            "identifies_objects": False,
        }


def _resolve(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_file():
        raise ValidationError(f"no such image: {resolved}")
    if resolved.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValidationError(
            f"unsupported image format '{resolved.suffix}'; "
            f"supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    return resolved


def analyse(path: str | Path, *, max_colours: int = 5) -> ImageAnalysis:
    """Measure an image. Offline, no model, always truthful."""
    if not pillow_available():
        raise ValidationError(
            "Pillow is not installed, so images cannot be read",
            details={"remedy": 'pip install -e ".[vision]"'},
        )

    from PIL import Image, ImageFilter, ImageStat

    resolved = _resolve(path)
    size_bytes = resolved.stat().st_size

    with Image.open(resolved) as image:
        fmt = (image.format or resolved.suffix.lstrip(".")).upper()
        animated = getattr(image, "n_frames", 1) > 1
        has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
        mode = image.mode
        width, height = image.size

        rgb = image.convert("RGB")
        # Analysis runs on a thumbnail: a 24-megapixel photo takes seconds to
        # measure at full size and gives the same answer.
        sample = rgb.copy()
        sample.thumbnail((320, 320))

        grey = sample.convert("L")
        stat = ImageStat.Stat(grey)
        brightness = stat.mean[0] / 255.0
        contrast = stat.stddev[0] / 255.0

        # Edge energy as a sharpness proxy. A blurred image has little.
        edges = grey.filter(ImageFilter.FIND_EDGES)
        sharpness = min(1.0, ImageStat.Stat(edges).mean[0] / 64.0)

        hsv = sample.convert("HSV")
        saturation = ImageStat.Stat(hsv).mean[1] / 255.0

        colours, flatness = _palette(sample, max_colours)

    return ImageAnalysis(
        path=str(resolved),
        width=width,
        height=height,
        fmt=fmt,
        size_bytes=size_bytes,
        mode=mode,
        colours=colours,
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        sharpness=sharpness,
        flatness=flatness,
        has_alpha=has_alpha,
        animated=animated,
    )


def _palette(image: Any, count: int) -> tuple[list[Colour], float]:
    """Dominant colours, and how concentrated the palette is.

    Colours are quantised into coarse bins before counting. Without that,
    a photograph returns several thousand near-identical shades and the
    "dominant" colour is whichever one happens to appear twice.
    """
    from PIL import Image

    reduced = image.quantize(colors=32, method=Image.Quantize.MEDIANCUT)
    palette = reduced.getpalette() or []
    counts = sorted(reduced.getcolors() or [], reverse=True)
    total = sum(n for n, _ in counts) or 1

    # Flatness comes from the raw quantised bins, before any merging. This is
    # the measurement that separates a screenshot from a photograph: a
    # screenshot's top three bins cover ~84% of the frame, a photograph's
    # cover ~12%. Computing it after merging by colour name destroyed the
    # signal entirely -- everything collapsed into a handful of named buckets
    # and every image scored 1.00, so every photograph was classified as a
    # screenshot.
    flatness = sum(pixels for pixels, _ in counts[:3]) / total

    merged: dict[str, tuple[int, tuple[int, int, int]]] = {}
    for pixels, index in counts:
        rgb = tuple(palette[index * 3 : index * 3 + 3])
        if len(rgb) < 3:
            continue
        name = colour_name(rgb)  # type: ignore[arg-type]
        # Merging is for presentation only: a reader wants "mostly blue", not
        # nine shades of it. The largest bin supplies the swatch.
        if name in merged:
            seen_pixels, seen_rgb = merged[name]
            best = rgb if pixels > seen_pixels else seen_rgb
            merged[name] = (seen_pixels + pixels, best)
        else:
            merged[name] = (pixels, rgb)

    ranked = sorted(merged.items(), key=lambda item: item[1][0], reverse=True)
    colours = [
        Colour(rgb=tuple(rgb), weight=pixels / total, name=name)  # type: ignore[arg-type]
        for name, (pixels, rgb) in ranked[:count]
    ]
    return colours, min(1.0, flatness)


# --------------------------------------------------------------------------- #
# multimodal transport
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ImagePayload:
    """An image prepared for a provider request."""

    data: str
    media_type: str
    width: int
    height: int
    bytes_sent: int
    resized: bool

    def to_data_url(self) -> str:
        return f"data:{self.media_type};base64,{self.data}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "width": self.width,
            "height": self.height,
            "bytes_sent": self.bytes_sent,
            "resized": self.resized,
        }


def prepare(path: str | Path, *, max_edge: int = MAX_EDGE_PX) -> ImagePayload:
    """Load an image and encode it for transmission.

    Downsamples anything larger than ``max_edge``. Every provider does this
    server-side anyway, so sending full resolution costs upload time and
    tokens without improving what is recognised.
    """
    if not pillow_available():
        raise ValidationError(
            "Pillow is not installed, so images cannot be encoded",
            details={"remedy": 'pip install -e ".[vision]"'},
        )

    import io

    from PIL import Image

    resolved = _resolve(path)
    media_type = _MIME[resolved.suffix.lower()]

    with Image.open(resolved) as image:
        width, height = image.size
        resized = max(width, height) > max_edge
        if resized:
            scale = max_edge / max(width, height)
            image = image.convert("RGB").resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
            media_type = "image/jpeg"
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            raw = buffer.getvalue()
            width, height = image.size
        else:
            raw = resolved.read_bytes()

    if len(raw) > MAX_IMAGE_BYTES:
        raise ValidationError(
            f"image is {len(raw) // 1_048_576} MB after encoding, over the "
            f"{MAX_IMAGE_BYTES // 1_048_576} MB provider limit",
            details={"remedy": "resize or re-compress the image"},
        )

    return ImagePayload(
        data=base64.b64encode(raw).decode("ascii"),
        media_type=media_type,
        width=width,
        height=height,
        bytes_sent=len(raw),
        resized=resized,
    )


def estimate_tokens(payload: ImagePayload) -> int:
    """Roughly how many tokens an image costs.

    Vision models tile an image and charge per tile. The exact arithmetic
    differs per provider; this is the common 512-pixel-tile approximation,
    which is close enough to warn someone before they send fifty photographs.
    """
    tiles = math.ceil(payload.width / 512) * math.ceil(payload.height / 512)
    return 85 + tiles * 170
