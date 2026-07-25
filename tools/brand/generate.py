"""Brand asset generator.

Draws the AERA mark and renders every size the project needs: the README
banner, application icons for all three platforms, and a favicon.

Everything is generated from code rather than checked in as binaries, so the
palette stays in sync with ``interface/src/design-system/colors.ts`` and the
assets rebuild deterministically.

    python -m tools.brand --out assets/brand
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Palette mirrors design-system/colors.ts.
BG_BASE = (7, 9, 15)
BG_RAISED = (11, 15, 23)
ACCENT = (77, 166, 255)
ACCENT_2 = (124, 92, 255)
TEXT = (233, 238, 248)
MUTED = (132, 148, 178)

#: Application icon sizes. ICO wants the small ones, ICNS the large.
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


# --------------------------------------------------------------------------- #
# drawing helpers
# --------------------------------------------------------------------------- #
def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def radial_glow(
    size: tuple[int, int],
    centre: tuple[float, float],
    radius: float,
    colour: tuple[int, int, int],
    strength: float = 1.0,
) -> Image.Image:
    """A soft radial falloff, drawn small and upscaled.

    Computing per-pixel at full resolution is slow; a low-res gradient scaled
    up with bicubic interpolation is visually identical for a soft glow.
    """
    steps = 96
    small = Image.new("RGBA", (steps, steps), (0, 0, 0, 0))
    pixels = small.load()
    assert pixels is not None

    for y in range(steps):
        for x in range(steps):
            dx = (x + 0.5) / steps - 0.5
            dy = (y + 0.5) / steps - 0.5
            distance = math.sqrt(dx * dx + dy * dy) * 2.0
            if distance >= 1.0:
                continue
            # Quadratic falloff reads softer than linear.
            alpha = (1.0 - distance) ** 2 * strength
            pixels[x, y] = (*colour, round(255 * min(1.0, alpha)))

    diameter = max(2, round(radius * 2))
    glow = small.resize((diameter, diameter), Image.Resampling.BICUBIC)

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.paste(glow, (round(centre[0] - radius), round(centre[1] - radius)), glow)
    return layer


def draw_mark(size: int, *, rings: bool = True, supersample: int = 4) -> Image.Image:
    """The AERA mark: a glowing core inside tilted orbital rings.

    Drawn at ``supersample`` times the target size and downscaled, which gives
    clean anti-aliased curves without any external rasteriser.
    """
    s = size * supersample
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    centre = s / 2

    # Outer atmospheric glow.
    canvas.alpha_composite(
        radial_glow((s, s), (centre, centre), s * 0.48, ACCENT, strength=0.30)
    )

    draw = ImageDraw.Draw(canvas)

    if rings:
        # Three ellipses at different tilts read as orbital motion frozen.
        for index, (rx_factor, ry_factor, angle, colour, width) in enumerate(
            (
                (0.44, 0.13, -22, ACCENT, 0.016),
                (0.40, 0.10, 34, ACCENT_2, 0.013),
                (0.46, 0.17, 8, ACCENT, 0.010),
            )
        ):
            ring = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            ring_draw = ImageDraw.Draw(ring)
            rx, ry = s * rx_factor, s * ry_factor
            ring_draw.ellipse(
                [centre - rx, centre - ry, centre + rx, centre + ry],
                outline=(*colour, 210 - index * 40),
                width=max(1, round(s * width)),
            )
            # Rotating the layer avoids the aliasing of a rotated-arc path.
            canvas.alpha_composite(ring.rotate(angle, resample=Image.Resampling.BICUBIC))

    # Core: bright centre fading to the secondary accent at the rim.
    core_r = s * 0.20
    core = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    core_draw = ImageDraw.Draw(core)
    layers = 48
    for i in range(layers, 0, -1):
        t = i / layers
        r = core_r * t
        # Highlight sits up and left, so the sphere reads as lit from there.
        offset = core_r * 0.16 * (1 - t)
        # Rim carries the violet; the body is accent blue heading to white at
        # the highlight. Blending from ACCENT_2 throughout made it read purple.
        rim_to_body = _lerp(ACCENT_2, ACCENT, min(1.0, (1 - t) * 2.2))
        colour = _lerp(rim_to_body, (214, 236, 255), max(0.0, (1 - t) - 0.45) * 1.8)
        core_draw.ellipse(
            [
                centre - r - offset,
                centre - r - offset,
                centre + r - offset,
                centre + r - offset,
            ],
            fill=(*colour, 255),
        )
    canvas.alpha_composite(core)

    # Inner bloom, tight around the core.
    canvas.alpha_composite(
        radial_glow((s, s), (centre, centre), core_r * 2.1, ACCENT, strength=0.55)
    )

    _ = draw
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Best available sans-serif, falling back to Pillow's bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font,
    fill,
    tracking: float = 0.0,
) -> float:
    """Draw text with letter spacing; returns the width consumed.

    Pillow has no tracking support, so each glyph is placed individually.
    """
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        advance = draw.textlength(char, font=font)
        x += advance + tracking
    return x - xy[0]


# --------------------------------------------------------------------------- #
# assets
# --------------------------------------------------------------------------- #
def make_banner(width: int = 1280, height: int = 400) -> Image.Image:
    """README banner: mark on the left, wordmark and tagline on the right."""
    image = Image.new("RGB", (width, height), BG_BASE)

    # Background: a vertical wash plus two off-centre colour pools.
    gradient = Image.new("RGB", (1, height))
    for y in range(height):
        gradient.putpixel((0, y), _lerp(BG_RAISED, BG_BASE, y / height))
    image.paste(gradient.resize((width, height), Image.Resampling.BILINEAR), (0, 0))

    canvas = image.convert("RGBA")
    canvas.alpha_composite(
        radial_glow((width, height), (width * 0.22, height * 0.5), height * 0.85, ACCENT, 0.22)
    )
    canvas.alpha_composite(
        radial_glow((width, height), (width * 0.78, height * 0.35), height * 0.7, ACCENT_2, 0.14)
    )

    # Faint grid, echoing the transcript panel in the interface.
    grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    for x in range(0, width, 40):
        grid_draw.line([(x, 0), (x, height)], fill=(*ACCENT, 10), width=1)
    for y in range(0, height, 40):
        grid_draw.line([(0, y), (width, y)], fill=(*ACCENT, 10), width=1)
    canvas.alpha_composite(grid)

    # Mark.
    mark_size = round(height * 0.68)
    mark = draw_mark(mark_size)
    canvas.alpha_composite(
        mark, (round(width * 0.11), round((height - mark_size) / 2))
    )

    draw = ImageDraw.Draw(canvas)
    text_x = width * 0.34

    title_font = _font(round(height * 0.20), bold=True)
    tagline_font = _font(round(height * 0.055))
    detail_font = _font(round(height * 0.042))

    title_y = height * 0.24
    _tracked_text(
        draw, (text_x, title_y), "AERA", title_font, TEXT, tracking=height * 0.035
    )

    draw.text(
        (text_x, title_y + height * 0.250),
        "Artificial Enhanced Reasoning Assistant",
        font=tagline_font,
        fill=ACCENT,
    )
    draw.text(
        (text_x, title_y + height * 0.330),
        "A native desktop AI operating system",
        font=detail_font,
        fill=MUTED,
    )

    # Feature chips.
    chip_y = title_y + height * 0.44
    chip_x = text_x
    chip_font = _font(round(height * 0.036))
    for label in ("Memory Graph", "31 Agents", "Local-First"):
        w = draw.textlength(label, font=chip_font)
        pad = height * 0.022
        draw.rounded_rectangle(
            [chip_x, chip_y, chip_x + w + pad * 2, chip_y + height * 0.075],
            radius=height * 0.038,
            outline=(*ACCENT, 90),
            width=1,
        )
        draw.text((chip_x + pad, chip_y + height * 0.019), label, font=chip_font, fill=MUTED)
        chip_x += w + pad * 2 + height * 0.03

    return canvas.convert("RGB")


def make_icon(size: int) -> Image.Image:
    """Square application icon with a rounded dark plate behind the mark."""
    supersample = 2 if size >= 256 else 4
    s = size * supersample

    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    plate = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        [0, 0, s - 1, s - 1], radius=s * 0.22, fill=(*BG_BASE, 255)
    )
    canvas.alpha_composite(plate)

    # Subtle inner rim so the icon has an edge on dark backgrounds.
    ImageDraw.Draw(canvas).rounded_rectangle(
        [1, 1, s - 2, s - 2],
        radius=s * 0.22,
        outline=(*ACCENT, 60),
        width=max(1, round(s * 0.006)),
    )

    # At tiny sizes the rings turn to mush, so drop them and enlarge the core.
    mark = draw_mark(round(s * (0.92 if size >= 48 else 1.05)), rings=size >= 48)
    offset = round((s - mark.width) / 2)
    canvas.alpha_composite(mark, (offset, offset))

    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def make_social(width: int = 1200, height: int = 630) -> Image.Image:
    """Open Graph card for link previews."""
    image = make_banner(width, round(width * 400 / 1280))
    card = Image.new("RGB", (width, height), BG_BASE)
    card.paste(image, (0, round((height - image.height) / 2)))
    return card


def make_wordmark(width: int = 600, height: int = 160) -> Image.Image:
    """Transparent horizontal lockup for docs and light backgrounds."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    mark_size = round(height * 0.82)
    canvas.alpha_composite(draw_mark(mark_size), (0, round((height - mark_size) / 2)))

    draw = ImageDraw.Draw(canvas)
    font = _font(round(height * 0.42), bold=True)
    _tracked_text(
        draw,
        (mark_size * 1.12, height * 0.28),
        "AERA",
        font,
        TEXT,
        tracking=height * 0.07,
    )
    return canvas


def make_favicon() -> Image.Image:
    """32px favicon, drawn without rings so it stays legible."""
    return make_icon(32)


# --------------------------------------------------------------------------- #
# writers
# --------------------------------------------------------------------------- #
def write_ico(path: Path, sizes: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)) -> Path:
    """Multi-resolution Windows ICO."""
    base = make_icon(256)
    path.parent.mkdir(parents=True, exist_ok=True)
    base.save(path, format="ICO", sizes=[(s, s) for s in sizes])
    return path


def write_icns(path: Path) -> Path:
    """macOS ICNS.

    Pillow's ICNS writer needs a 1024px source and emits the standard set.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    make_icon(1024).save(path, format="ICNS")
    return path


def generate_all(out: Path) -> list[tuple[str, Path, tuple[int, int]]]:
    """Write every asset, returning (label, path, dimensions)."""
    out.mkdir(parents=True, exist_ok=True)
    icons_dir = out / "icons"
    icons_dir.mkdir(exist_ok=True)

    written: list[tuple[str, Path, tuple[int, int]]] = []

    def save(label: str, image: Image.Image, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        written.append((label, path, image.size))

    save("banner", make_banner(), out / "banner.png")
    save("banner (2x)", make_banner(2560, 800), out / "banner@2x.png")
    save("social card", make_social(), out / "social-card.png")
    save("wordmark", make_wordmark(), out / "wordmark.png")

    for size in ICON_SIZES:
        save(f"icon {size}px", make_icon(size), icons_dir / f"icon-{size}.png")

    save("favicon", make_favicon(), out / "favicon.png")

    ico = write_ico(icons_dir / "icon.ico")
    written.append(("icon.ico (Windows)", ico, (256, 256)))

    try:
        icns = write_icns(icons_dir / "icon.icns")
        written.append(("icon.icns (macOS)", icns, (1024, 1024)))
    except (OSError, ValueError) as exc:  # pragma: no cover - Pillow build dependent
        print(f"  note: could not write ICNS ({exc})")

    return written
