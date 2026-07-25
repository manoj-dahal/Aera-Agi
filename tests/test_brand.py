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

    def test_rings_can_be_dropped(self):
        """Small icons omit the rings, so the two forms must differ."""
        with_rings = draw_mark(256, rings=True)
        without = draw_mark(256, rings=False)
        assert list(with_rings.getdata()) != list(without.getdata())

    def test_core_reads_as_the_accent_colour(self):
        """A regression: the core once rendered lavender, not accent blue."""
        mark = draw_mark(256).convert("RGBA")
        centre = mark.getpixel((128, 128))
        r, g, b, a = centre
        assert a > 200, "core should be opaque at the centre"
        assert b >= g >= r, f"core is not blue-dominant: {centre}"


class TestIcons:
    @pytest.mark.parametrize("size", ICON_SIZES)
    def test_every_size_renders(self, size):
        icon = make_icon(size)
        assert icon.size == (size, size)
        assert icon.mode == "RGBA"

    def test_small_icons_drop_the_rings(self):
        """Three overlapping ellipses are illegible at 16px.

        Compare the horizontal extent of bright pixels: with rings the mark
        spans nearly the full width, without them it is a centred core.
        """
        def bright_span(image):
            width, height = image.size
            row = height // 2
            xs = [
                x
                for x in range(width)
                if sum(image.getpixel((x, row))[:3]) > 240
            ]
            return (max(xs) - min(xs)) / width if xs else 0.0

        assert bright_span(make_icon(32)) < bright_span(make_icon(256))

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
