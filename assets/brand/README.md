# Brand assets

Generated from code, not checked in by hand:

```bash
python -m tools.brand                  # writes here
python -m tools.brand --install-icons  # also copies icons into installer/
```

The palette is taken from `interface/src/design-system/colors.ts`, so the
assets stay in sync with the interface rather than drifting from it.

| File | Size | Use |
|---|---|---|
| `banner.png` | 1280×400 | README header |
| `banner@2x.png` | 2560×800 | high-DPI displays |
| `social-card.png` | 1200×630 | Open Graph link previews |
| `wordmark.png` | 600×160 | transparent lockup for docs |
| `favicon.png` | 32×32 | browser tab |
| `icons/icon-{16…1024}.png` | various | PNG icon set |
| `icons/icon.ico` | multi-res | Windows executable |
| `icons/icon.icns` | 1024 | macOS app bundle |

## The mark

An eye at the centre of a neon cyan ring, with four pairs of signal arcs
radiating from it over a dark starfield. The eye is perception, the arcs are
listening — which suits a voice-first assistant better than the orbital rings
this replaced.

Everything is drawn with Pillow at 2–4× and downsampled with Lanczos, so
curves are clean without needing an external rasteriser. The neon comes from
two Gaussian bloom passes over a single cyan layer: a tight one for the edge
and a wide one for the spill.

### Detail drops out as the icon shrinks

Fine strokes turn to noise once a supersampled render is downscaled, so
`make_icon()` sheds layers on the way down:

| Size | Ring | Eye | Arcs | Starfield |
|---|:-:|:-:|:-:|:-:|
| 16–24px | ✓ | | | |
| 32–47px | ✓ | ✓ | | |
| 48–63px | ✓ | ✓ | ✓ | |
| 64px+ | ✓ | ✓ | ✓ | ✓ |

At 16px the mark is a ring around a bright pupil, which still reads as the
same badge in a taskbar. `tests/test_brand.py` counts distinct bright runs
across the midline to hold that ladder in place.

## Regenerating

Change the palette in the design system, rerun the generator, and every asset
follows. If you edit `installer/icon.ico` or `icon.icns` by hand they will be
overwritten on the next `--install-icons`.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
