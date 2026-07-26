# Your avatar models

Drop your 3D models in this folder:

```
/home/user/Aera-Agi/storage/avatars/anime-g.glb    # feminine
/home/user/Aera-Agi/storage/avatars/anime-b.glb    # masculine
```

Then pick them up:

```bash
curl -X POST http://localhost:8080/api/v1/avatars/scan
```

Or just restart AERA — it scans on startup. You can also upload without
copying files:

```bash
curl -F file=@anime-g.glb http://localhost:8080/api/v1/avatars/upload
```

> **Note on paths.** `/home/user/Aera-Agi/` is the repository checkout. When
> running the packaged desktop app, state lives in the OS app-data directory
> instead — `~/.local/share/AERA/avatars/` on Linux,
> `~/Library/Application Support/AERA/avatars/` on macOS, `%APPDATA%\AERA\avatars\`
> on Windows. **Help → Open Data Folder** in the app takes you straight there.

Nothing in this folder is committed to git except this README.

## Formats

| Format | Parsed | Notes |
|---|---|---|
| **`.glb`** | yes | **Recommended.** Geometry, materials, textures and rigging in one file. |
| `.gltf` | yes | Keep the `.bin` and texture files alongside it. |
| `.obj` | yes | Keep the `.mtl` and textures in the same folder. |
| `.fbx` | catalogued only | Proprietary binary; no open Python parser. Export to GLB. |
| `.vrm` | catalogued only | VRM is glTF-based — export GLB from your tool. |

## Seeing it render

Once a model is in place, open **Hologram** in the interface. Select a model
and it replaces the particle orb on the Dashboard, lit with a three-point rig
and an emotion-tinted rim light. Rotation, breathing and sway follow the same
state machine as the orb, so the two are interchangeable.

You can also drag files straight onto the model library on that page.

The renderer is three.js, loaded on demand. If you never select a model, that
~624 kB never downloads.

## What AERA checks

On scan, each model is inspected and reported with:

- vertex and triangle counts, bounding box, materials, textures
- whether it has normals, UVs and a skeleton
- **morph targets** (shape keys) and which of AERA's six visemes they bind to
- **warnings** for anything that will break rendering: out-of-range face
  indices, missing normals or UVs, a missing `.mtl`, an implausible export
  scale, or an empty file

Nothing is silently repaired. If a file has a problem you are told what it is.

## Lip-sync

Speech drives morph targets, so a model needs mouth shape keys for its lips to
move. AERA emits six visemes — `open`, `closed`, `teeth`, `tongue`, `narrow`,
`neutral` — and binds each to whatever your rig calls them. These conventions
are all recognised:

| Convention | Example keys |
|---|---|
| Oculus / Meta | `viseme_aa`, `viseme_PP`, `viseme_FF`, `viseme_sil` |
| ARKit | `jawOpen`, `mouthClose`, `mouthFunnel`, `mouthPucker` |
| VRM / VRChat | `vrc.v_aa`, `vrc.v_pp`, `vrc.v_ss` |
| Blender single letters | `A`, `E`, `O`, `M`, `F`, `Basis` |

Case and separators are ignored, so `Viseme_AA`, `viseme aa` and `VISEMEAA`
are the same key.

A model needs at least **open** and **closed** to lip-sync — one mouth shape
alone reads as a twitch, not speech. The Hologram page shows a `lip-sync` tag
when a model qualifies and how many of the six visemes were bound. If a model
has shape keys but none match, you get a warning saying so rather than silent
stillness.

> **Exporting from Blender:** shape key names travel in `mesh.extras.targetNames`.
> Tick **Shape Keys** under Geometry when exporting glTF, or the targets ship
> unnamed and nothing can tell which is which.

## Naming

The filename tells AERA what the model is and which figure it represents.

**Kind** — from any token in the name:

| Contains | Kind |
|---|---|
| `anime`, `avatar`, `char`, `girl`, `boy`, `human`, `person` | `character` |
| `orb`, `sphere`, `core`, `ball` | `orb` |

**Variant** — from the **last** token only:

| Suffix | Variant |
|---|---|
| `-g`, `-f`, `-girl`, `-female` | `feminine` |
| `-b`, `-m`, `-boy`, `-male` | `masculine` |
| `-n`, `-nb`, `-neutral` | `neutral` |

So the pair:

```
anime-g.glb   ->  character / feminine
anime-b.glb   ->  character / masculine
```

Separators are interchangeable — `anime-g`, `anime_g` and `anime.g` all work.
Only the trailing token is read, so a file called `boyd-model.glb` is *not*
mistaken for masculine.

Filter the library by either:

```bash
curl "localhost:8080/api/v1/avatars?variant=feminine"
curl "localhost:8080/api/v1/avatars?kind=character"
```

## Limits

512 MB per file. Beyond roughly 2 million triangles most renderers become
sluggish; if you have a high-poly sculpt, decimate it and bake the detail into
normal maps.
