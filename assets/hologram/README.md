# Hologram assets

AERA ships **no avatar model of its own**. Supply your own — see
`storage/avatars/README.md`.

## Placeholder generator

`tools/meshgen` builds simple base meshes if you want something to test the
pipeline with before your own model is ready:

```bash
python -m tools.meshgen --out assets/hologram              # ~4 MB each
python -m tools.meshgen --target-mb 100 --microdetail 0.3  # ~97 MB each
```

| Asset | Notes |
|---|---|
| `voice_orb.obj` | Displaced icosphere with three orbital rings |
| `anime_girl.obj` | 1.58 m, 6.6 head ratio |
| `anime_boy.obj` | 1.72 m, 6.9 head ratio |

Options: `--target-mb` solves for the polygon count that lands near a file
size; `--anatomy` scales anatomical relief (clavicle, scapula, knee caps);
`--microdetail` adds skin-scale surface noise in millimetres.

These are **base meshes**, not finished characters — no facial features,
fingers, rig or blendshapes. They exist to exercise the loader. A model you
author will be better.

Generated files are gitignored; they rebuild deterministically from a seed.

---

**MADE By Manoj Dahal** · Copyright © 2026 Manoj Dahal. All rights reserved.
Contact: [info@manoj-dahal.com.np](mailto:info@manoj-dahal.com.np)
