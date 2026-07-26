"""Avatar model loader.

Loads user-supplied 3D models for the hologram avatar. AERA ships no character
of its own by default: you drop a model into the avatars directory and it is
discovered, validated and served.

Supported formats:

* ``.obj``  - Wavefront, with optional ``.mtl`` and texture maps
* ``.gltf`` - glTF 2.0, JSON form with external buffers
* ``.glb``  - glTF 2.0, binary container (preferred: single file, embedded textures)
* ``.fbx``  - detected and catalogued, but not parsed (see FBX_NOTE)

Validation is deliberately strict about the things that break renderers -
missing files, malformed indices, absurd scale - and quiet about the things
that are merely stylistic.
"""

from __future__ import annotations

import json
import shutil
import struct
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..core.errors import NotFoundError, ValidationError
from ..core.logging import get_logger

logger = get_logger("hologram.loader")

FBX_NOTE = (
    "FBX is a proprietary binary format with no open parser in the Python "
    "standard library. Export to GLB or OBJ from your DCC tool; GLB is "
    "preferred because it carries textures and rigging in one file."
)

#: Formats the loader can parse and report geometry for.
PARSEABLE = {".obj", ".gltf", ".glb"}
#: Formats recognised as avatars but not parsed.
RECOGNISED = PARSEABLE | {".fbx", ".vrm"}

#: Texture extensions collected alongside a model.
TEXTURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"}

#: A model larger than this is almost certainly a mistake or a bad unit scale.
MAX_MODEL_BYTES = 512 * 1024 * 1024

#: Substrings that identify a morph target for each viseme AERA emits.
#:
#: ``aera.voice.engine._VISEME_MAP`` produces six shapes. Riggers name their
#: shape keys with no shared convention -- ARKit uses ``jawOpen``, VRM uses
#: ``A``/``I``/``U``, Oculus uses ``viseme_aa``, and Blender exports whatever
#: the artist typed -- so each shape is matched against several spellings.
#: Ordered most to least specific; the first hit wins.
_VISEME_ALIASES: dict[str, tuple[str, ...]] = {
    "open": ("viseme_aa", "jawopen", "mouthopen", "vrc.v_aa", "aa", "ah", "a", "e", "o"),
    "closed": ("viseme_pp", "mouthclose", "vrc.v_pp", "mouthpress", "pp", "mbp", "m", "closed"),
    "teeth": ("viseme_ff", "vrc.v_ff", "mouthfunnel", "ff", "fv"),
    "tongue": ("viseme_dd", "viseme_nn", "vrc.v_dd", "tonguout", "tongueout", "dd", "nn", "l"),
    # "sil" is silence, not a narrow mouth -- it belongs to neutral, and
    # listing it here let narrow claim vrc.v_sil first.
    "narrow": ("viseme_ss", "vrc.v_ss", "mouthpucker", "mouthnarrow", "ss", "u"),
    "neutral": ("viseme_sil", "vrc.v_sil", "sil", "neutral", "rest", "basis", "idle"),
}


def _normalise_morph_name(name: str) -> str:
    """Lower-case and strip separators so spellings compare equal.

    ``Viseme_AA``, ``viseme aa`` and ``visemeAA`` all reduce to ``visemeaa``.
    """
    return "".join(c for c in name.lower() if c.isalnum())


def match_visemes(targets: Sequence[str]) -> dict[str, str]:
    """Bind AERA's viseme shapes to a model's morph target names.

    Returns ``{shape: target_name}`` for every shape that could be matched.
    A target is claimed by at most one shape, so a model whose only mouth key
    is ``jawOpen`` maps ``open`` and honestly reports nothing else.
    """
    if not targets:
        return {}

    normalised = {name: _normalise_morph_name(name) for name in targets}
    bindings: dict[str, str] = {}
    claimed: set[str] = set()

    for shape, aliases in _VISEME_ALIASES.items():
        for alias in aliases:
            key = _normalise_morph_name(alias)
            # Exact match first: "a" must not be satisfied by "jawOpen".
            hit = next(
                (n for n, norm in normalised.items() if norm == key and n not in claimed),
                None,
            )
            if hit is None and len(key) > 2:
                # Then substring, but only for names long enough to be
                # unambiguous -- "a" as a substring matches almost anything.
                hit = next(
                    (n for n, norm in normalised.items() if key in norm and n not in claimed),
                    None,
                )
            if hit is not None:
                bindings[shape] = hit
                claimed.add(hit)
                break

    return bindings


class AvatarKind(str, Enum):
    """What the model represents, inferred from its name or declared."""

    CHARACTER = "character"
    ORB = "orb"
    PROP = "prop"
    UNKNOWN = "unknown"


class AvatarVariant(str, Enum):
    """Which figure a character model is.

    Recognised from a suffix on the filename so a set like ``anime-g`` /
    ``anime-b`` is paired automatically and labelled correctly in the UI.
    """

    FEMININE = "feminine"
    MASCULINE = "masculine"
    NEUTRAL = "neutral"
    UNSPECIFIED = "unspecified"


#: Filename suffixes mapping to a variant. Checked after the stem is split on
#: the usual separators, so "anime-g", "anime_girl" and "aera.f" all resolve.
_VARIANT_TOKENS: dict[str, AvatarVariant] = {
    "g": AvatarVariant.FEMININE,
    "f": AvatarVariant.FEMININE,
    "girl": AvatarVariant.FEMININE,
    "female": AvatarVariant.FEMININE,
    "woman": AvatarVariant.FEMININE,
    "b": AvatarVariant.MASCULINE,
    "m": AvatarVariant.MASCULINE,
    "boy": AvatarVariant.MASCULINE,
    "male": AvatarVariant.MASCULINE,
    "man": AvatarVariant.MASCULINE,
    "n": AvatarVariant.NEUTRAL,
    "neutral": AvatarVariant.NEUTRAL,
    "nb": AvatarVariant.NEUTRAL,
}


@dataclass
class AvatarModel:
    """A discovered avatar model and everything known about it."""

    id: str
    name: str
    path: Path
    format: str
    kind: AvatarKind = AvatarKind.UNKNOWN
    variant: AvatarVariant = AvatarVariant.UNSPECIFIED
    size_bytes: int = 0
    #: Populated for parseable formats; None when the format is not parsed.
    vertices: int | None = None
    triangles: int | None = None
    materials: list[str] = field(default_factory=list)
    textures: list[str] = field(default_factory=list)
    #: Bounding box in model units, as (min, max).
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None
    has_normals: bool = False
    has_uvs: bool = False
    has_skeleton: bool = False
    #: Morph target ("shape key") names, in glTF target order. Lip-sync and
    #: expressions drive these, so an avatar without them can still be
    #: rendered but cannot mouth words.
    morph_targets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed: bool = False

    @property
    def has_morph_targets(self) -> bool:
        return bool(self.morph_targets)

    @property
    def viseme_bindings(self) -> dict[str, str]:
        """Map AERA's viseme shapes onto this model's morph target names."""
        return match_visemes(self.morph_targets)

    @property
    def can_lip_sync(self) -> bool:
        """Whether speech can move this model's mouth.

        A model needs at least the open/closed pair for lip movement to read
        as speech rather than a twitch.
        """
        bindings = self.viseme_bindings
        return "open" in bindings and "closed" in bindings

    @property
    def dimensions(self) -> tuple[float, float, float] | None:
        if self.bounds is None:
            return None
        low, high = self.bounds
        return (high[0] - low[0], high[1] - low[1], high[2] - low[2])

    def to_dict(self) -> dict[str, Any]:
        dims = self.dimensions
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "format": self.format,
            "kind": self.kind.value,
            "variant": self.variant.value,
            "size_mb": round(self.size_bytes / 1_048_576, 2),
            "vertices": self.vertices,
            "triangles": self.triangles,
            "materials": self.materials,
            "textures": self.textures,
            "dimensions": [round(d, 2) for d in dims] if dims else None,
            "has_normals": self.has_normals,
            "has_uvs": self.has_uvs,
            "has_skeleton": self.has_skeleton,
            "morph_targets": self.morph_targets,
            "has_morph_targets": self.has_morph_targets,
            "viseme_bindings": self.viseme_bindings,
            "can_lip_sync": self.can_lip_sync,
            "warnings": self.warnings,
            "parsed": self.parsed,
        }


# --------------------------------------------------------------------------- #
# format parsers
# --------------------------------------------------------------------------- #
def parse_obj(path: Path, *, max_scan_bytes: int = 200 * 1024 * 1024) -> dict[str, Any]:
    """Read an OBJ's geometry summary without building the full mesh.

    Streams the file line by line so a 100 MB model costs memory proportional
    to the bounding box, not the vertex list.
    """
    vertices = uvs = normals = triangles = 0
    materials: list[str] = []
    mtllib: str | None = None
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    warnings: list[str] = []
    bad_indices = 0

    size = path.stat().st_size
    if size > max_scan_bytes:
        warnings.append(
            f"file is {size / 1_048_576:.0f} MB; scanned headers only"
        )

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    vertices += 1
                    try:
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    except ValueError:
                        continue
                    for i, value in enumerate((x, y, z)):
                        lo[i] = min(lo[i], value)
                        hi[i] = max(hi[i], value)
            elif line.startswith("vt "):
                uvs += 1
            elif line.startswith("vn "):
                normals += 1
            elif line.startswith("f "):
                corners = len(line.split()) - 1
                if corners >= 3:
                    # An n-gon triangulates to n-2 triangles.
                    triangles += corners - 2
                    for token in line.split()[1:]:
                        try:
                            index = int(token.split("/")[0])
                        except ValueError:
                            bad_indices += 1
                            break
                        if index == 0 or index > vertices:
                            bad_indices += 1
                            break
            elif line.startswith("mtllib "):
                mtllib = line.split(maxsplit=1)[1].strip()
            elif line.startswith("usemtl "):
                material = line.split(maxsplit=1)[1].strip()
                if material not in materials:
                    materials.append(material)

    if bad_indices:
        warnings.append(f"{bad_indices} face(s) reference out-of-range vertices")
    if vertices == 0:
        warnings.append("no vertices found; the file may not be a valid OBJ")
    if normals == 0:
        warnings.append("no vertex normals; the renderer will flat-shade")
    if uvs == 0:
        warnings.append("no UV coordinates; textures cannot be applied")

    bounds = None
    if vertices and lo[0] != float("inf"):
        bounds = (tuple(lo), tuple(hi))  # type: ignore[assignment]

    return {
        "vertices": vertices,
        "triangles": triangles,
        "materials": materials,
        "mtllib": mtllib,
        "bounds": bounds,
        "has_normals": normals > 0,
        "has_uvs": uvs > 0,
        "has_skeleton": False,
        # OBJ is a static format: no rig, no shape keys.
        "morph_targets": [],
        "warnings": warnings,
    }


def parse_gltf(path: Path) -> dict[str, Any]:
    """Read a glTF 2.0 or GLB header.

    Both forms share the same JSON schema; GLB wraps it in a binary container,
    so the chunk is extracted first.
    """
    if path.suffix.lower() == ".glb":
        document = _read_glb_json(path)
    else:
        document = json.loads(path.read_text(encoding="utf-8"))

    warnings: list[str] = []
    accessors = document.get("accessors", [])
    meshes = document.get("meshes", [])

    vertices = 0
    triangles = 0
    has_normals = False
    has_uvs = False

    morph_targets: list[str] = []

    for mesh in meshes:
        # Morph target names live in mesh.extras.targetNames by convention --
        # glTF has no first-class field for them. Without names a model still
        # animates, but nothing can tell which target is which mouth shape.
        target_names = (mesh.get("extras") or {}).get("targetNames") or []
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            position = attributes.get("POSITION")
            if position is not None and position < len(accessors):
                vertices += accessors[position].get("count", 0)
            if "NORMAL" in attributes:
                has_normals = True
            if "TEXCOORD_0" in attributes:
                has_uvs = True

            targets = primitive.get("targets") or []
            for index in range(len(targets)):
                name = (
                    target_names[index]
                    if index < len(target_names)
                    else f"{mesh.get('name', 'mesh')}_target_{index}"
                )
                if name not in morph_targets:
                    morph_targets.append(name)

            indices = primitive.get("indices")
            if indices is not None and indices < len(accessors):
                triangles += accessors[indices].get("count", 0) // 3
            elif position is not None and position < len(accessors):
                triangles += accessors[position].get("count", 0) // 3

    # Bounding box: the POSITION accessor carries min/max per the spec.
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    found = False
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            position = primitive.get("attributes", {}).get("POSITION")
            if position is None or position >= len(accessors):
                continue
            accessor = accessors[position]
            a_min, a_max = accessor.get("min"), accessor.get("max")
            if a_min and a_max and len(a_min) >= 3:
                found = True
                for i in range(3):
                    lo[i] = min(lo[i], a_min[i])
                    hi[i] = max(hi[i], a_max[i])

    materials = [m.get("name", f"material_{i}") for i, m in enumerate(document.get("materials", []))]
    textures = [
        image.get("uri", f"embedded_{i}")
        for i, image in enumerate(document.get("images", []))
    ]
    skins = document.get("skins", [])

    if not has_normals:
        warnings.append("no NORMAL attribute; the renderer will flat-shade")
    if not has_uvs:
        warnings.append("no TEXCOORD_0; textures cannot be applied")
    if not meshes:
        warnings.append("document contains no meshes")
    if morph_targets and not match_visemes(morph_targets):
        # Having shape keys but none recognisable is worth saying: the model
        # can be posed, but speech will not move its mouth.
        warnings.append(
            f"{len(morph_targets)} morph target(s) but none match a viseme; "
            "lip-sync will not drive this model"
        )

    return {
        "vertices": vertices,
        "triangles": triangles,
        "materials": materials,
        "textures": [t for t in textures if not t.startswith("data:")],
        "bounds": (tuple(lo), tuple(hi)) if found else None,
        "has_normals": has_normals,
        "has_uvs": has_uvs,
        "has_skeleton": bool(skins),
        "morph_targets": morph_targets,
        "warnings": warnings,
    }


def _read_glb_json(path: Path) -> dict[str, Any]:
    """Extract the JSON chunk from a GLB container."""
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) < 12:
            raise ValidationError(f"{path.name} is too short to be a GLB file")
        magic, version, _ = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise ValidationError(f"{path.name} is not a GLB file (bad magic)")
        if version != 2:
            raise ValidationError(f"{path.name} is GLB version {version}; only 2 is supported")

        chunk_header = handle.read(8)
        if len(chunk_header) < 8:
            raise ValidationError(f"{path.name} has no JSON chunk")
        length, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != 0x4E4F534A:  # 'JSON'
            raise ValidationError(f"{path.name}: first chunk is not JSON")

        payload = handle.read(length)

    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{path.name}: malformed glTF JSON: {exc}") from exc


# --------------------------------------------------------------------------- #
# library
# --------------------------------------------------------------------------- #
class AvatarLibrary:
    """Discovers and validates user-supplied avatar models."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self._models: dict[str, AvatarModel] = {}
        self._active: str | None = None

    # ------------------------------------------------------------------ #
    # discovery
    # ------------------------------------------------------------------ #
    def scan(self) -> list[AvatarModel]:
        """Find every recognised model under the avatars directory.

        Zips dropped in by hand are unpacked first: a marketplace download is
        an archive, and requiring the user to unzip it themselves is friction
        for no reason.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        self._models.clear()

        for archive in sorted(self.root.glob("*.zip")):
            try:
                extract_archive(archive, self.root / archive.stem)
            except Exception as exc:  # noqa: BLE001 - a bad zip must not stop the scan
                logger.warning("could not unpack %s: %s", archive.name, exc)
                continue
            logger.info("unpacked %s", archive.name)
            archive.unlink(missing_ok=True)

        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in RECOGNISED:
                continue
            try:
                model = self._inspect(path)
            except Exception as exc:  # noqa: BLE001 - one bad file must not stop the scan
                logger.warning("could not read %s: %s", path.name, exc)
                model = AvatarModel(
                    id=_model_id(path, self.root),
                    name=path.stem,
                    path=path,
                    format=suffix.lstrip("."),
                    size_bytes=path.stat().st_size,
                    warnings=[f"could not read: {exc}"],
                )
            self._models[model.id] = model

        logger.info("avatar library: %d model(s) in %s", len(self._models), self.root)
        return list(self._models.values())

    def _inspect(self, path: Path) -> AvatarModel:
        suffix = path.suffix.lower()
        size = path.stat().st_size

        model = AvatarModel(
            id=_model_id(path, self.root),
            name=_naming_stem(path).replace("_", " ").replace("-", " ").strip(),
            path=path,
            format=suffix.lstrip("."),
            kind=_infer_kind(path),
            variant=_infer_variant(path),
            size_bytes=size,
        )

        if size > MAX_MODEL_BYTES:
            model.warnings.append(
                f"{size / 1_048_576:.0f} MB exceeds the {MAX_MODEL_BYTES // 1_048_576} MB "
                "limit; most renderers will struggle"
            )
            return model

        if size == 0:
            model.warnings.append("file is empty")
            return model

        if suffix == ".obj":
            data = parse_obj(path)
            model.textures = self._sidecar_textures(path, data.get("mtllib"))
        elif suffix in (".gltf", ".glb"):
            data = parse_gltf(path)
        else:
            # FBX and VRM are recognised but not parsed.
            model.warnings.append(
                FBX_NOTE if suffix == ".fbx" else f"{suffix} is catalogued but not parsed"
            )
            return model

        model.vertices = data["vertices"]
        model.triangles = data["triangles"]
        model.materials = data["materials"]
        model.textures = model.textures or data.get("textures", [])
        model.bounds = data["bounds"]
        model.has_normals = data["has_normals"]
        model.has_uvs = data["has_uvs"]
        model.has_skeleton = data["has_skeleton"]
        model.morph_targets = data.get("morph_targets", [])
        model.warnings.extend(data["warnings"])
        model.parsed = True

        self._check_scale(model)
        return model

    def _sidecar_textures(self, model_path: Path, mtllib: str | None) -> list[str]:
        """Textures referenced by an OBJ's MTL, plus any in the same folder."""
        found: list[str] = []

        if mtllib:
            mtl_path = model_path.parent / mtllib
            if mtl_path.is_file():
                for line in mtl_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[0].lower().startswith(("map_", "norm", "bump")):
                        found.append(parts[-1])
            else:
                found.append(f"(missing: {mtllib})")

        for sibling in model_path.parent.iterdir():
            if sibling.suffix.lower() in TEXTURE_EXTENSIONS and sibling.name not in found:
                found.append(sibling.name)

        return found

    @staticmethod
    def _check_scale(model: AvatarModel) -> None:
        """Flag a model whose units look wrong.

        Characters authored in metres, centimetres and millimetres all appear;
        a height far outside the plausible band usually means the exporter's
        unit scale was not set.
        """
        dims = model.dimensions
        if not dims or model.kind is not AvatarKind.CHARACTER:
            return
        height = max(dims)
        if height <= 0:
            model.warnings.append("model has zero extent")
        elif height < 0.1:
            model.warnings.append(f"height is {height:.3f} units; check the export scale")
        elif height > 100_000:
            model.warnings.append(f"height is {height:.0f} units; check the export scale")

    # ------------------------------------------------------------------ #
    # access
    # ------------------------------------------------------------------ #
    def all(self) -> list[AvatarModel]:
        return list(self._models.values())

    def get(self, model_id: str) -> AvatarModel:
        model = self._models.get(model_id)
        if model is None:
            raise NotFoundError(f"avatar model not found: {model_id}")
        return model

    def by_kind(self, kind: AvatarKind | str) -> list[AvatarModel]:
        value = AvatarKind(kind)
        return [m for m in self._models.values() if m.kind is value]

    def by_variant(self, variant: AvatarVariant | str) -> list[AvatarModel]:
        value = AvatarVariant(variant)
        return [m for m in self._models.values() if m.variant is value]

    @property
    def active(self) -> AvatarModel | None:
        return self._models.get(self._active) if self._active else None

    def set_active(self, model_id: str) -> AvatarModel:
        model = self.get(model_id)
        self._active = model_id
        logger.info("active avatar: %s", model.name)
        return model

    def summary(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "count": len(self._models),
            "active": self._active,
            "by_kind": {
                kind.value: len(self.by_kind(kind))
                for kind in AvatarKind
                if self.by_kind(kind)
            },
            "by_variant": {
                variant.value: len(self.by_variant(variant))
                for variant in AvatarVariant
                if self.by_variant(variant)
            },
            "with_warnings": sum(1 for m in self._models.values() if m.warnings),
            "supported_formats": sorted(f.lstrip(".") for f in RECOGNISED),
        }


def extract_archive(archive: Path, destination: Path) -> list[Path]:
    """Unpack a model archive, returning the model files it contained.

    Marketplaces hand out zips rather than bare models -- Sketchfab's layout
    is ``scene.gltf`` plus ``scene.bin`` and a ``textures/`` folder, all of
    which must stay together for the glTF to resolve its references.

    Extraction is deliberately defensive:

    * entries escaping the destination (``../``, absolute paths, symlinks)
      are refused outright rather than skipped quietly
    * the uncompressed total is capped, so a zip bomb cannot fill the disk
    * junk the loader cannot use (``__MACOSX``, ``.DS_Store``) is dropped
    """
    if not zipfile.is_zipfile(archive):
        raise ValidationError(f"{archive.name} is not a valid zip archive")

    keep = RECOGNISED | TEXTURE_EXTENSIONS | {".mtl", ".bin"}
    destination.mkdir(parents=True, exist_ok=True)
    resolved_root = destination.resolve()

    extracted: list[Path] = []
    total = 0

    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if info.is_dir():
                continue

            name = info.filename
            if name.startswith("__MACOSX/") or Path(name).name.startswith("._"):
                continue
            if Path(name).name == ".DS_Store":
                continue
            if Path(name).suffix.lower() not in keep:
                continue

            # Zip-slip: reject absolute paths and anything climbing out.
            target = (destination / name).resolve()
            if not target.is_relative_to(resolved_root):
                raise ValidationError(
                    f"archive entry escapes the destination: {name}"
                )

            total += info.file_size
            if total > MAX_MODEL_BYTES:
                raise ValidationError(
                    f"archive expands to more than "
                    f"{MAX_MODEL_BYTES // 1_048_576} MB"
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            extracted.append(target)

    models = [p for p in extracted if p.suffix.lower() in RECOGNISED]
    if not models:
        raise ValidationError(
            f"{archive.name} contains no model file "
            f"({', '.join(sorted(f.lstrip('.') for f in RECOGNISED))})"
        )
    return models


def _model_id(path: Path, root: Path) -> str:
    """Stable id from the path relative to the library root."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = Path(path.name)
    return str(relative.with_suffix("")).replace("/", ".").replace("\\", ".")


#: Filenames exporters emit that say nothing about the model. When a file is
#: called one of these, the containing folder carries the real name --
#: Sketchfab bundles are always "scene.gltf" inside a named directory.
_GENERIC_STEMS = frozenset(
    {"scene", "model", "untitled", "export", "mesh", "character", "avatar"}
)


def _naming_stem(path: Path) -> str:
    """The part of the path that actually names the model."""
    stem = path.stem.lower()
    if stem in _GENERIC_STEMS and path.parent.name:
        return path.parent.name.lower()
    return stem


def _infer_variant(path: Path) -> AvatarVariant:
    """Infer the figure from a filename suffix.

    Splits the stem on the usual separators and checks the trailing token, so
    ``anime-g`` and ``anime_girl`` both resolve to feminine. Only the last
    token is consulted - a project called "boyd-model" must not be read as
    masculine.

    Falls back to the parent directory when the file has a generic exporter
    name, so ``anime-g/scene.gltf`` is still feminine.
    """
    import re

    tokens = [t for t in re.split(r"[-_. ]+", _naming_stem(path)) if t]
    if not tokens:
        return AvatarVariant.UNSPECIFIED
    return _VARIANT_TOKENS.get(tokens[-1], AvatarVariant.UNSPECIFIED)


def _infer_kind(path: Path) -> AvatarKind:
    """Guess what a model represents from its filename."""
    name = _naming_stem(path)
    if any(token in name for token in ("orb", "sphere", "core", "ball")):
        return AvatarKind.ORB
    if any(
        token in name
        for token in ("girl", "boy", "char", "avatar", "human", "person", "man", "woman", "anime")
    ):
        return AvatarKind.CHARACTER
    return AvatarKind.UNKNOWN
