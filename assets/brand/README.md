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

A glowing core inside three tilted orbital rings — the same shape the
dashboard renders as a live particle sphere, frozen into a static form.

Everything is drawn with Pillow at 4× and downsampled with Lanczos, so curves
are clean without needing an external rasteriser.

**Below 48px the rings are dropped** and the core is enlarged instead. At 16px
three overlapping ellipses turn to mush; a single bright core stays legible.
The contact sheet in `tools/brand/generate.py` docstrings explains the sizes.

## Regenerating

Change the palette in the design system, rerun the generator, and every asset
follows. If you edit `installer/icon.ico` or `icon.icns` by hand they will be
overwritten on the next `--install-icons`.
