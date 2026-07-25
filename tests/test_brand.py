"""Tests for the brand asset generator.

The installer references icon.ico and icon.icns by path; if those are missing
the packaged Windows and macOS builds ship without an icon, and PyInstaller
fails only at build time. These tests catch that in CI instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tools.brand.generate import (
    ICON_SIZES,
    draw_mark,
    make_banner,
    make_favicon,
    make_icon,
    make_social,
    make_wordmark,
    write_ico,
)

REPO = Path(__file__).resolve().parent.parent


class TestMark:
    def test_renders_at_the_requested_size(self):
        assert draw_mark(128).size == (128, 128)

    def test_has_transparency(self):
        """The mark composites onto any background, so it must not be opaque."""
        mark = draw_mark(64)
        assert mark.mode == "RGBA"
        assert mark.getextrema()[3][0] == 0, "no fully transparent pixels"

    def test_has_visible_content(self):
        mark = draw_mark(64)
        assert mark.getextrema()[3][1] > 200, "mark is nearly invisible"

    @pytest.mark.parametrize("detail", ["arcs", "stars", "iris"])
    def test_detail_layers_can_be_dropped(self, detail):
        """Each layer small icons shed must actually change the render."""
        full = draw_mark(256)
        stripped = draw_mark(256, **{detail: False})
        assert list(full.getdata()) != list(stripped.getdata())

    def test_pupil_is_white(self):
        """The eye's pupil is the one white element; everything else is cyan."""
        mark = draw_mark(256).convert("RGBA")
        r, g, b, a = mark.getpixel((128, 128))
        assert a > 200, "pupil should be opaque at the centre"
        assert min(r, g, b) > 230, f"pupil is not white: {(r, g, b)}"

    def test_ring_is_brand_cyan(self):
        """A regression guard: the mark once rendered blue, then lavender.

        Cyan means green and blue both high and close, with red well below.
        Sampled on the ring at the horizontal midline.
        """
        mark = draw_mark(256).convert("RGBA")
        row = 128
        lit = [
            mark.getpixel((x, row))
            for x in range(mark.width - 1, mark.width // 2, -1)
            if mark.getpixel((x, row))[3] > 200
        ]
        assert lit, "no opaque pixels found on the ring"
        r, g, b, _ = max(lit[:8], key=lambda px: px[1] + px[2])
        assert g > 150 and b > 150, f"ring is too dark to be neon: {(r, g, b)}"
        assert r < g * 0.6, f"ring is not cyan-dominant: {(r, g, b)}"
        assert abs(g - b) < 60, f"cyan should have green close to blue: {(r, g, b)}"


class TestIcons:
    @pytest.mark.parametrize("size", ICON_SIZES)
    def test_every_size_renders(self, size):
        icon = make_icon(size)
        assert icon.size == (size, size)
        assert icon.mode == "RGBA"

    def test_small_icons_shed_detail(self):
        """The eye and its signal arcs are illegible at 16px.

        Span is the wrong measure now that the mark is a ring badge at every
        size -- the ring always reaches the edge. Count distinct bright runs
        across the midline instead: the ring alone gives 3 (left edge, pupil,
        right edge), the eye adds its outline, the arcs add four more.
        """
        def features(image):
            width, height = image.size
            row = height // 2
            count = 0
            previous = False
            for x in range(width):
                pixel = image.getpixel((x, row))
                lit = pixel[3] > 128 and sum(pixel[:3]) > 240
                count += lit and not previous
                previous = lit
            return count

        assert features(make_icon(16)) == 3, "16px should be ring plus pupil only"
        assert features(make_icon(32)) > features(make_icon(16)), "32px should show the eye"
        assert features(make_icon(64)) > features(make_icon(32)), "64px should show the arcs"

    def test_icons_are_not_blank(self):
        for size in (16, 64, 256):
            icon = make_icon(size)
            assert icon.getextrema()[3][1] > 200, f"{size}px icon is blank"

    def test_ico_is_multi_resolution(self, tmp_path):
        path = write_ico(tmp_path / "icon.ico")
        assert path.is_file()
        with Image.open(path) as image:
            assert image.size[0] >= 256


class TestCompositions:
    def test_banner_dimensions(self):
        assert make_banner().size == (1280, 400)
        assert make_banner(2560, 800).size == (2560, 800)

    def test_social_card_is_open_graph_sized(self):
        assert make_social().size == (1200, 630)

    def test_social_card_has_no_letterbox_seams(self):
        """The card used to paste a banner strip onto a flat plate.

        That left two hard horizontal edges where the gradient stopped. The
        background is now painted at full height, so a vertical scan down the
        left margin must not contain an abrupt jump.
        """
        card = make_social().convert("RGB")
        x = 18  # between the 40px grid lines, so only the wash is sampled
        # The grid draws every 40px; those rows are a deliberate step.
        rows = [y for y in range(card.height) if y % 40 not in (0, 39)]
        for previous_y, y in zip(rows, rows[1:], strict=False):  # pairwise
            if y - previous_y != 1:
                continue
            before = card.getpixel((x, previous_y))
            after = card.getpixel((x, y))
            delta = max(abs(after[i] - before[i]) for i in range(3))
            assert delta <= 6, f"hard seam at y={y}: {before} -> {after}"

    def test_wordmark_is_transparent(self):
        wordmark = make_wordmark()
        assert wordmark.mode == "RGBA"
        assert wordmark.getpixel((wordmark.width - 2, 2))[3] == 0

    def test_favicon_is_32px(self):
        assert make_favicon().size == (32, 32)

    def test_banner_is_not_a_flat_field(self):
        """Catches a generator that silently produces an empty rectangle."""
        banner = make_banner(320, 100).convert("RGB")
        colours = banner.getcolors(maxcolors=1_000_000)
        assert colours is not None and len(colours) > 500


class TestGeneratedFilesExist:
    """The repo ships these; a missing one breaks the README or the installer."""

    @pytest.mark.parametrize(
        "relative",
        [
            "assets/brand/banner.png",
            "assets/brand/social-card.png",
            "assets/brand/wordmark.png",
            "assets/brand/favicon.png",
            "assets/brand/icons/icon-256.png",
            "assets/brand/icons/icon.ico",
        ],
    )
    def test_asset_is_present(self, relative):
        assert (REPO / relative).is_file(), f"missing {relative}; run python -m tools.brand"

    @pytest.mark.parametrize("name", ["icon.ico", "icon.icns"])
    def test_installer_icons_are_present(self, name):
        """installer/aera.spec references these; PyInstaller fails without them."""
        assert (REPO / "installer" / name).is_file(), (
            f"installer/{name} missing; run python -m tools.brand --install-icons"
        )

    def test_readme_references_the_banner(self):
        assert "assets/brand/banner.png" in (REPO / "README.md").read_text()

    def test_web_apps_reference_the_favicon(self):
        for relative in ("interface/index.html", "aera/desktop/ui/index.html"):
            assert "favicon.png" in (REPO / relative).read_text(), f"{relative} has no favicon"


class TestCli:
    def test_generates_a_full_set(self, tmp_path):
        from tools.brand.__main__ import main

        assert main(["--out", str(tmp_path)]) == 0
        assert (tmp_path / "banner.png").is_file()
        assert (tmp_path / "icons" / "icon.ico").is_file()
        # Every declared size must be written.
        for size in ICON_SIZES:
            assert (tmp_path / "icons" / f"icon-{size}.png").is_file()
