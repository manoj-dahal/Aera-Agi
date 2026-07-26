# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Brand asset generator.

Draws the AERA mark and renders every size the project needs: the README
banner, application icons for all three platforms, and a favicon.

The mark is the supplied logo rebuilt as geometry: a neon cyan ring enclosing
a dark starfield plate, with an eye at the centre and four pairs of signal
arcs radiating from it. Eye for perception, arcs for listening -- which suits
a voice-first assistant better than the orbital rings this replaced.

Everything is generated from code rather than checked in as opaque binaries,
so the palette stays in sync with ``interface/src/design-system/colors.ts``
and the assets rebuild deterministically.

    python -m tools.brand --out assets/brand
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Palette mirrors design-system/colors.ts.
BG_BASE = (7, 9, 15)
BG_RAISED = (11, 15, 23)
#: Brand cyan, sampled from the supplied logo.
ACCENT = (64, 232, 240)
#: Shadowed cyan, used where the accent needs to fall off into the plate.
ACCENT_DEEP = (16, 118, 152)
ACCENT_2 = (124, 92, 255)
TEXT = (233, 238, 248)
MUTED = (132, 148, 178)

#: The dark plate inside the ring: near-black at the rim, faint teal wash in
#: the middle so the starfield has something to sit on.
DISC_CORE = (10, 30, 44)
DISC_EDGE = (3, 7, 13)

#: Application icon sizes. ICO wants the small ones, ICNS the large.
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)

# --------------------------------------------------------------------------- #
# mark geometry
#
# RING_R is a fraction of the canvas; everything else is a fraction of the
# resulting disc radius, so the mark scales as one piece.
# --------------------------------------------------------------------------- #
RING_R = 0.478
RING_WIDTH = 0.036
STROKE = 0.031

EYE_HALF_W = 0.370
EYE_HALF_H = 0.180
IRIS_R = 0.167
PUPIL_R = 0.066
#: Pupil size when the eye outline is dropped, so 16px icons still read.
PUPIL_R_SIMPLE = 0.30

#: (radius, half-sweep in degrees) for each arc, outermost first.
VERTICAL_ARCS = ((0.410, 35.0), (0.310, 33.0))
HORIZONTAL_ARCS = ((0.575, 31.0), (0.435, 28.0))

#: Fixed seed keeps the starfield identical between builds.
STARFIELD_SEED = 0xAE7A


# --------------------------------------------------------------------------- #
# drawing helpers
# --------------------------------------------------------------------------- #
def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _scale_alpha(image: Image.Image, factor: float) -> Image.Image:
    """Uniformly dim a layer, for stacking bloom passes."""
    out = image.copy()
    out.putalpha(out.getchannel("A").point(lambda v: min(255, round(v * factor))))
    return out


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


def _round_arc(
    draw: ImageDraw.ImageDraw,
    centre: tuple[float, float],
    radius: float,
    start: float,
    end: float,
    width: float,
    colour: tuple[int, int, int],
) -> None:
    """Stroke an arc with rounded caps.

    Pillow's ``arc`` leaves butt ends; the logo's arcs are capsule-shaped, so
    a disc is stamped at each endpoint.
    """
    cx, cy = centre
    stroke = max(1, round(width))
    draw.arc(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        start,
        end,
        fill=colour,
        width=stroke,
    )
    cap = stroke / 2
    # Pillow strokes inward from the bounding box, so the cap sits on the
    # centreline of the band, not on the nominal radius.
    centreline = radius - cap
    for angle in (start, end):
        radians = math.radians(angle)
        px = cx + centreline * math.cos(radians)
        py = cy + centreline * math.sin(radians)
        draw.ellipse([px - cap, py - cap, px + cap, py + cap], fill=colour)


def _vesica(
    centre: tuple[float, float],
    half_w: float,
    half_h: float,
    samples: int = 160,
) -> list[tuple[float, float]]:
    """Outline of a pointed oval (the eye), built from two circular arcs.

    A vesica through (±half_w, 0) and (0, ±half_h) is cut from two circles of
    radius ``r`` whose centres sit ``r - half_h`` either side of the middle.
    """
    cx, cy = centre
    r = (half_w * half_w + half_h * half_h) / (2 * half_h)
    offset = r - half_h
    span = math.asin(min(1.0, half_w / r))

    points: list[tuple[float, float]] = []
    for i in range(samples + 1):
        t = -span + (2 * span) * i / samples
        points.append((cx + r * math.sin(t), cy + offset - r * math.cos(t)))
    for i in range(samples + 1):
        t = span - (2 * span) * i / samples
        points.append((cx + r * math.sin(t), cy - offset + r * math.cos(t)))
    return points


def _vesica_inset(
    centre: tuple[float, float],
    half_w: float,
    half_h: float,
    inset: float,
    samples: int = 160,
) -> list[tuple[float, float]]:
    """The inner edge of a stroked vesica: the same arcs, ``inset`` smaller.

    Offsetting concentric arcs keeps the tips genuinely pointed, which a
    naive polyline stroke would blunt.
    """
    cx, cy = centre
    r = (half_w * half_w + half_h * half_h) / (2 * half_h)
    offset = r - half_h
    inner_r = r - inset
    if inner_r <= offset:
        return []
    inner_w = math.sqrt(inner_r * inner_r - offset * offset)
    inner_h = inner_r - offset
    return _vesica(centre, inner_w, inner_h, samples)


def _starfield(diameter: int, seed: int = STARFIELD_SEED) -> Image.Image:
    """Scattered stars and a few cyan bokeh blooms, clipped to the plate."""
    rng = random.Random(seed)
    layer = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    radius = diameter / 2

    # A handful of out-of-focus points, drawn first so stars sit on top.
    for _ in range(5):
        distance = radius * 0.82 * math.sqrt(rng.random())
        angle = rng.uniform(0, math.tau)
        bokeh_r = diameter * rng.uniform(0.020, 0.036)
        layer.alpha_composite(
            radial_glow(
                (diameter, diameter),
                (radius + distance * math.cos(angle), radius + distance * math.sin(angle)),
                bokeh_r,
                ACCENT,
                strength=rng.uniform(0.45, 0.85),
            )
        )

    draw = ImageDraw.Draw(layer)
    count = max(24, round(diameter * diameter / 12_000))
    for _ in range(count):
        # sqrt() keeps the density even across the area rather than clumping
        # everything into the middle.
        distance = radius * 0.955 * math.sqrt(rng.random())
        angle = rng.uniform(0, math.tau)
        x = radius + distance * math.cos(angle)
        y = radius + distance * math.sin(angle)
        star_r = diameter * rng.uniform(0.0013, 0.0036)
        colour = _lerp((255, 255, 255), ACCENT, rng.random() * 0.45)
        draw.ellipse(
            [x - star_r, y - star_r, x + star_r, y + star_r],
            fill=(*colour, round(rng.uniform(130, 255))),
        )
    return layer


def _plate(diameter: int, stars: bool) -> Image.Image:
    """The dark disc inside the ring."""
    steps = 128
    small = Image.new("RGB", (steps, steps), DISC_EDGE)
    pixels = small.load()
    assert pixels is not None
    for y in range(steps):
        for x in range(steps):
            dx = (x + 0.5) / steps - 0.5
            dy = (y + 0.5) / steps - 0.5
            distance = min(1.0, math.sqrt(dx * dx + dy * dy) * 2.0)
            pixels[x, y] = _lerp(DISC_EDGE, DISC_CORE, max(0.0, 1.0 - distance**1.4))

    plate = small.resize((diameter, diameter), Image.Resampling.BICUBIC).convert("RGBA")
    if stars:
        plate.alpha_composite(_starfield(diameter))

    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter - 1, diameter - 1], fill=255)
    plate.putalpha(mask)
    return plate


def draw_mark(
    size: int,
    *,
    arcs: bool = True,
    stars: bool = True,
    iris: bool = True,
    supersample: int = 4,
) -> Image.Image:
    """The AERA mark: an eye inside a neon ring, ringed by signal arcs.

    Drawn at ``supersample`` times the target size and downscaled, which gives
    clean anti-aliased curves without any external rasteriser.

    ``arcs``, ``stars`` and ``iris`` strip detail for small icons, where the
    fine strokes would turn to mush.
    """
    s = size * supersample
    centre = s / 2
    radius = s * RING_R
    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # Strokes must survive the downscale, so never go below one output pixel.
    ring_w = max(supersample, round(radius * RING_WIDTH))
    stroke = max(supersample, round(radius * STROKE))

    # Atmospheric halo outside the ring. Two falloffs stacked: a broad one
    # that fills the corners and a tight one that hugs the rim, which is what
    # makes the ring read as emitting rather than merely being cyan.
    canvas.alpha_composite(
        radial_glow((s, s), (centre, centre), radius * 1.34, ACCENT, strength=0.30)
    )
    canvas.alpha_composite(
        radial_glow((s, s), (centre, centre), radius * 1.10, ACCENT, strength=0.55)
    )

    # Dark plate.
    plate_d = max(2, round((radius - ring_w * 0.5) * 2))
    canvas.alpha_composite(
        _plate(plate_d, stars), (round(centre - plate_d / 2), round(centre - plate_d / 2))
    )

    # Everything cyan goes on one layer so a single bloom pass lights it all.
    glyph = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glyph)

    gd.ellipse(
        [centre - radius, centre - radius, centre + radius, centre + radius],
        outline=ACCENT,
        width=ring_w,
    )

    if arcs:
        for factor, sweep in VERTICAL_ARCS:
            arc_r = radius * factor
            # Pillow measures clockwise from 3 o'clock with y pointing down,
            # so 270 is the top of the circle and 90 the bottom.
            _round_arc(gd, (centre, centre), arc_r, 270 - sweep, 270 + sweep, stroke, ACCENT)
            _round_arc(gd, (centre, centre), arc_r, 90 - sweep, 90 + sweep, stroke, ACCENT)
        for factor, sweep in HORIZONTAL_ARCS:
            arc_r = radius * factor
            _round_arc(gd, (centre, centre), arc_r, 180 - sweep, 180 + sweep, stroke, ACCENT)
            _round_arc(gd, (centre, centre), arc_r, 360 - sweep, 360 + sweep, stroke, ACCENT)

    if iris:
        half_w = radius * EYE_HALF_W
        half_h = radius * EYE_HALF_H
        gd.polygon(_vesica((centre, centre), half_w, half_h), fill=ACCENT)
        inner = _vesica_inset((centre, centre), half_w, half_h, stroke)
        if inner:
            gd.polygon(inner, fill=(0, 0, 0, 0))

        iris_r = radius * IRIS_R
        gd.ellipse(
            [centre - iris_r, centre - iris_r, centre + iris_r, centre + iris_r],
            outline=ACCENT,
            width=stroke,
        )

    # Two bloom passes: a tight one for the neon edge, a wide one for spill.
    canvas.alpha_composite(
        _scale_alpha(glyph.filter(ImageFilter.GaussianBlur(max(1.0, s * 0.009))), 0.80)
    )
    canvas.alpha_composite(
        _scale_alpha(glyph.filter(ImageFilter.GaussianBlur(max(1.0, s * 0.026))), 0.55)
    )
    canvas.alpha_composite(glyph)

    # Pupil last, so the bloom does not wash out its white centre.
    pupil_r = radius * (PUPIL_R if iris else PUPIL_R_SIMPLE)
    canvas.alpha_composite(
        radial_glow((s, s), (centre, centre), pupil_r * 3.4, ACCENT, strength=0.75)
    )
    pupil = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(pupil).ellipse(
        [centre - pupil_r, centre - pupil_r, centre + pupil_r, centre + pupil_r],
        fill=(255, 255, 255, 255),
    )
    canvas.alpha_composite(
        _scale_alpha(pupil.filter(ImageFilter.GaussianBlur(max(1.0, pupil_r * 0.55))), 0.9)
    )
    canvas.alpha_composite(pupil)

    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def make_svg(size: int = 64, *, arcs: bool = True) -> str:
    """The mark as a standalone SVG, for the plain HTML shells.

    Those pages are served without a bundler, so an inline vector avoids both
    a network round-trip and a raster that blurs on a HiDPI screen. It shares
    the geometry constants above, so it cannot drift from the PNGs.
    """
    accent = "#{:02X}{:02X}{:02X}".format(*ACCENT)
    # viewBox is a unit circle scaled to 100, so the constants read directly.
    r = 100 * RING_R
    stroke = r * STROKE
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'width="{size}" height="{size}" fill="none" '
        f'stroke="{accent}" stroke-width="{stroke:.2f}" stroke-linecap="round" '
        f'role="img" aria-label="AERA">',
        f'<circle cx="50" cy="50" r="{r:.2f}" stroke-width="{r * RING_WIDTH:.2f}"/>',
    ]

    if arcs:
        for factor, sweep in VERTICAL_ARCS:
            for base in (270.0, 90.0):
                parts.append(_svg_arc(r * factor, base - sweep, base + sweep))
        for factor, sweep in HORIZONTAL_ARCS:
            for base in (180.0, 360.0):
                parts.append(_svg_arc(r * factor, base - sweep, base + sweep))

    # Eye: two symmetric circular arcs meeting at the corners, matching the
    # vesica the raster path builds.
    half_w = r * EYE_HALF_W
    half_h = r * EYE_HALF_H
    radius = (half_w * half_w + half_h * half_h) / (2 * half_h)
    parts.append(
        f'<path d="M{50 - half_w:.2f} 50'
        f'A{radius:.2f} {radius:.2f} 0 0 1 {50 + half_w:.2f} 50'
        f'A{radius:.2f} {radius:.2f} 0 0 1 {50 - half_w:.2f} 50Z"/>'
    )
    parts.append(f'<circle cx="50" cy="50" r="{r * IRIS_R:.2f}"/>')
    parts.append(f'<circle cx="50" cy="50" r="{r * PUPIL_R:.2f}" fill="#FFFFFF" stroke="none"/>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_arc(radius: float, start: float, end: float) -> str:
    """One arc of the signal pattern, as an SVG path."""
    x1 = 50 + radius * math.cos(math.radians(start))
    y1 = 50 + radius * math.sin(math.radians(start))
    x2 = 50 + radius * math.cos(math.radians(end))
    y2 = 50 + radius * math.sin(math.radians(end))
    large = 1 if (end - start) % 360 > 180 else 0
    return f'<path d="M{x1:.2f} {y1:.2f}A{radius:.2f} {radius:.2f} 0 {large} 1 {x2:.2f} {y2:.2f}"/>'


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
def _backdrop(width: int, height: int, focus: float = 0.5) -> Image.Image:
    """Shared background: vertical wash, colour pools and a faint grid.

    ``focus`` is where the glow pools sit vertically, so a taller card can
    keep them centred on content that is not itself centred.
    """
    image = Image.new("RGB", (width, height), BG_BASE)

    gradient = Image.new("RGB", (1, height))
    for y in range(height):
        gradient.putpixel((0, y), _lerp(BG_RAISED, BG_BASE, y / height))
    image.paste(gradient.resize((width, height), Image.Resampling.BILINEAR), (0, 0))

    canvas = image.convert("RGBA")
    canvas.alpha_composite(
        radial_glow((width, height), (width * 0.22, height * focus), width * 0.27, ACCENT, 0.20)
    )
    canvas.alpha_composite(
        radial_glow(
            (width, height),
            (width * 0.78, height * (focus - 0.15)),
            width * 0.22,
            ACCENT_DEEP,
            0.18,
        )
    )

    # Faint grid, echoing the transcript panel in the interface.
    grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    for x in range(0, width, 40):
        grid_draw.line([(x, 0), (x, height)], fill=(*ACCENT, 10), width=1)
    for y in range(0, height, 40):
        grid_draw.line([(0, y), (width, y)], fill=(*ACCENT, 10), width=1)
    canvas.alpha_composite(grid)
    return canvas


def make_banner(
    width: int = 1280,
    height: int = 400,
    *,
    backdrop: Image.Image | None = None,
    offset_y: int = 0,
) -> Image.Image:
    """README banner: mark on the left, wordmark and tagline on the right.

    ``backdrop`` and ``offset_y`` let the social card supply a taller,
    full-bleed background and drop this content into the middle of it,
    instead of pasting a letterboxed strip that leaves visible seams.
    """
    canvas = _backdrop(width, height) if backdrop is None else backdrop.copy()

    # Mark.
    mark_size = round(height * 0.68)
    mark = draw_mark(mark_size)
    canvas.alpha_composite(
        mark, (round(width * 0.11), round((height - mark_size) / 2) + offset_y)
    )

    draw = ImageDraw.Draw(canvas)
    text_x = width * 0.34

    title_font = _font(round(height * 0.20), bold=True)
    tagline_font = _font(round(height * 0.055))
    detail_font = _font(round(height * 0.042))

    title_y = height * 0.24 + offset_y
    _tracked_text(
        draw, (text_x, title_y), "AERA", title_font, TEXT, tracking=height * 0.035
    )

    draw.text(
        (text_x, title_y + height * 0.250),
        "Artificial Voice Reasoning Assistant",
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
    """Square application icon: the mark, full bleed, on transparency.

    The mark is already a circular badge with its own dark plate, so a second
    rounded-rectangle plate behind it would only add visible corners.
    """
    return draw_mark(
        size,
        # Below these thresholds the detail collapses into noise once the
        # supersampled render is downscaled.
        arcs=size >= 48,
        stars=size >= 64,
        iris=size >= 28,
        supersample=2 if size >= 256 else 4,
    )


def make_social(width: int = 1200, height: int = 630) -> Image.Image:
    """Open Graph card for link previews.

    The banner's layout is proportional to its height, so rendering it at the
    full 630px would oversize the type. Instead the content keeps banner
    proportions and is centred on a backdrop painted at the card's real size,
    which avoids the letterbox seams a pasted strip leaves behind.
    """
    content_h = round(width * 400 / 1280)
    backdrop = _backdrop(width, height, focus=0.5)
    return make_banner(
        width,
        content_h,
        backdrop=backdrop,
        offset_y=round((height - content_h) / 2),
    )


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
    """32px favicon, stripped back so it stays legible in a tab."""
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
