# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Tests for the user-supplied avatar model loader.

The contract: AERA accepts models the user provides, tells them honestly what
is wrong with a file, and never silently mangles or deletes something outside
the library.
"""

from __future__ import annotations

import json
import struct

import pytest

from aera.core.errors import NotFoundError, ValidationError
from aera.hologram.loader import (
    RECOGNISED,
    AvatarKind,
    AvatarLibrary,
    AvatarVariant,
    extract_archive,
    match_visemes,
    parse_gltf,
    parse_obj,
)

MINIMAL_OBJ = """\
mtllib model.mtl
v 0 0 0
v 1 0 0
v 0 1 0
v 1 1 0
vt 0 0
vt 1 0
vt 0 1
vt 1 1
vn 0 0 1
usemtl skin
f 1/1/1 2/2/1 3/3/1
f 2/2/1 4/4/1 3/3/1
"""


def write_glb(path, document: dict) -> None:
    """Pack a glTF JSON document into a valid GLB container."""
    payload = json.dumps(document).encode()
    payload += b" " * ((4 - len(payload) % 4) % 4)
    header = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(payload))
    chunk = struct.pack("<II", len(payload), 0x4E4F534A)
    path.write_bytes(header + chunk + payload)


GLTF_DOC = {
    "asset": {"version": "2.0"},
    "meshes": [
        {
            "primitives": [
                {
                    "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                    "indices": 3,
                }
            ]
        }
    ],
    "accessors": [
        {"count": 1000, "type": "VEC3", "min": [-0.5, 0.0, -0.3], "max": [0.5, 1.7, 0.3]},
        {"count": 1000, "type": "VEC3"},
        {"count": 1000, "type": "VEC2"},
        {"count": 3000, "type": "SCALAR"},
    ],
    "materials": [{"name": "skin"}, {"name": "hair"}],
    "images": [{"uri": "skin_4k.png"}],
    "skins": [{"joints": [0, 1, 2]}],
}


@pytest.fixture
def library(tmp_path):
    return AvatarLibrary(tmp_path / "avatars")


class TestObjParsing:
    def test_reads_geometry(self, tmp_path):
        path = tmp_path / "m.obj"
        path.write_text(MINIMAL_OBJ)
        data = parse_obj(path)
        assert data["vertices"] == 4
        assert data["triangles"] == 2
        assert data["has_normals"] and data["has_uvs"]
        assert data["materials"] == ["skin"]

    def test_triangulates_ngons(self, tmp_path):
        """A quad face is two triangles; a pentagon is three."""
        path = tmp_path / "m.obj"
        path.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nv 2 2 0\nf 1 2 3 4\nf 1 2 3 4 5\n")
        assert parse_obj(path)["triangles"] == 2 + 3

    def test_computes_bounds(self, tmp_path):
        path = tmp_path / "m.obj"
        path.write_text("v -2 0 -1\nv 3 5 4\nv 0 1 0\n")
        low, high = parse_obj(path)["bounds"]
        assert low == (-2.0, 0.0, -1.0)
        assert high == (3.0, 5.0, 4.0)

    def test_flags_out_of_range_indices(self, tmp_path):
        """A face referencing a missing vertex crashes real renderers."""
        path = tmp_path / "m.obj"
        path.write_text("v 0 0 0\nf 1 2 3\n")
        warnings = parse_obj(path)["warnings"]
        assert any("out-of-range" in w for w in warnings)

    def test_flags_missing_normals_and_uvs(self, tmp_path):
        path = tmp_path / "m.obj"
        path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        warnings = parse_obj(path)["warnings"]
        assert any("normals" in w for w in warnings)
        assert any("UV" in w for w in warnings)

    def test_empty_file_is_flagged(self, tmp_path):
        path = tmp_path / "m.obj"
        path.write_text("")
        assert any("no vertices" in w for w in parse_obj(path)["warnings"])

    def test_tolerates_malformed_lines(self, tmp_path):
        path = tmp_path / "m.obj"
        path.write_text("v 0 0 0\nv not a number here\nv 1 1 1\nf 1 2 3\n")
        assert parse_obj(path)["vertices"] == 3  # counted, bad values skipped


class TestGltfParsing:
    def test_reads_a_gltf_document(self, tmp_path):
        path = tmp_path / "m.gltf"
        path.write_text(json.dumps(GLTF_DOC))
        data = parse_gltf(path)
        assert data["vertices"] == 1000
        assert data["triangles"] == 1000
        assert data["has_skeleton"] is True
        assert data["materials"] == ["skin", "hair"]

    def test_reads_a_glb_container(self, tmp_path):
        path = tmp_path / "m.glb"
        write_glb(path, GLTF_DOC)
        data = parse_gltf(path)
        assert data["vertices"] == 1000
        assert data["bounds"][1][1] == pytest.approx(1.7)

    def test_rejects_bad_magic(self, tmp_path):
        path = tmp_path / "m.glb"
        path.write_bytes(b"NOPE" + b"\x00" * 40)
        with pytest.raises(ValidationError, match="not a GLB"):
            parse_gltf(path)

    def test_rejects_a_truncated_glb(self, tmp_path):
        path = tmp_path / "m.glb"
        path.write_bytes(b"glTF")
        with pytest.raises(ValidationError):
            parse_gltf(path)

    def test_rejects_glb_version_one(self, tmp_path):
        path = tmp_path / "m.glb"
        path.write_bytes(b"glTF" + struct.pack("<II", 1, 20) + struct.pack("<II", 0, 0x4E4F534A))
        with pytest.raises(ValidationError, match="version 1"):
            parse_gltf(path)

    def test_flags_a_document_with_no_meshes(self, tmp_path):
        path = tmp_path / "m.gltf"
        path.write_text(json.dumps({"asset": {"version": "2.0"}}))
        assert any("no meshes" in w for w in parse_gltf(path)["warnings"])


class TestLibrary:
    def test_creates_the_directory(self, library):
        library.scan()
        assert library.root.is_dir()

    def test_empty_library(self, library):
        assert library.scan() == []
        assert library.summary()["count"] == 0

    def test_discovers_models(self, library):
        library.root.mkdir(parents=True)
        (library.root / "hero.obj").write_text(MINIMAL_OBJ)
        write_glb(library.root / "heroine.glb", GLTF_DOC)
        assert len(library.scan()) == 2

    def test_ignores_unrelated_files(self, library):
        library.root.mkdir(parents=True)
        (library.root / "hero.obj").write_text(MINIMAL_OBJ)
        (library.root / "notes.txt").write_text("hello")
        (library.root / "archive.zip").write_bytes(b"PK")
        assert len(library.scan()) == 1

    @pytest.mark.parametrize(
        "filename,kind",
        [
            ("anime_girl.obj", AvatarKind.CHARACTER),
            ("my_avatar.glb", AvatarKind.CHARACTER),
            ("voice_orb.obj", AvatarKind.ORB),
            ("energy_sphere.glb", AvatarKind.ORB),
            ("thing.obj", AvatarKind.UNKNOWN),
        ],
    )
    def test_infers_kind_from_the_name(self, library, filename, kind):
        library.root.mkdir(parents=True)
        target = library.root / filename
        # Write content matching the extension; a GLB with OBJ text inside is
        # correctly rejected, which would mask what this test is checking.
        if target.suffix == ".glb":
            write_glb(target, GLTF_DOC)
        else:
            target.write_text(MINIMAL_OBJ)
        assert library.scan()[0].kind is kind

    def test_fbx_is_catalogued_but_not_parsed(self, library):
        library.root.mkdir(parents=True)
        (library.root / "from_maya.fbx").write_bytes(b"Kaydara FBX Binary\x00" + b"\x00" * 64)
        model = library.scan()[0]
        assert model.parsed is False
        assert model.vertices is None
        assert any("GLB" in w for w in model.warnings), "should suggest a workable format"

    def test_collects_sidecar_textures(self, library):
        library.root.mkdir(parents=True)
        (library.root / "hero.obj").write_text(MINIMAL_OBJ)
        (library.root / "model.mtl").write_text("newmtl skin\nmap_Kd skin_4k.png\n")
        (library.root / "skin_4k.png").write_bytes(b"\x89PNG")
        assert "skin_4k.png" in library.scan()[0].textures

    def test_flags_a_missing_mtl(self, library):
        library.root.mkdir(parents=True)
        (library.root / "hero.obj").write_text(MINIMAL_OBJ)  # references model.mtl
        assert any("missing" in t for t in library.scan()[0].textures)

    def test_flags_an_implausible_scale(self, library):
        """A character 0.001 units tall means the export scale was wrong."""
        library.root.mkdir(parents=True)
        (library.root / "avatar_tiny.obj").write_text(
            "v 0 0 0\nv 0.001 0.001 0.001\nv 0 0.001 0\nf 1 2 3\n"
        )
        assert any("scale" in w for w in library.scan()[0].warnings)

    def test_a_broken_file_does_not_stop_the_scan(self, library):
        library.root.mkdir(parents=True)
        (library.root / "good.obj").write_text(MINIMAL_OBJ)
        (library.root / "bad.glb").write_bytes(b"not a glb at all")
        models = library.scan()
        assert len(models) == 2
        assert any(m.warnings for m in models)

    def test_empty_file_is_flagged(self, library):
        library.root.mkdir(parents=True)
        (library.root / "empty.obj").write_text("")
        assert any("empty" in w for w in library.scan()[0].warnings)

    def test_get_and_missing(self, library):
        library.root.mkdir(parents=True)
        (library.root / "hero.obj").write_text(MINIMAL_OBJ)
        model = library.scan()[0]
        assert library.get(model.id).name == model.name
        with pytest.raises(NotFoundError):
            library.get("does-not-exist")

    def test_set_active(self, library):
        library.root.mkdir(parents=True)
        (library.root / "hero.obj").write_text(MINIMAL_OBJ)
        model = library.scan()[0]
        assert library.active is None
        library.set_active(model.id)
        assert library.active is not None and library.active.id == model.id

    def test_finds_models_in_subdirectories(self, library):
        nested = library.root / "characters" / "main"
        nested.mkdir(parents=True)
        (nested / "hero.obj").write_text(MINIMAL_OBJ)
        models = library.scan()
        assert len(models) == 1
        assert "characters" in models[0].id


class TestVariantDetection:
    """The user's naming scheme is anime-g / anime-b; both must resolve."""

    @pytest.mark.parametrize(
        "filename,variant",
        [
            ("anime-g.glb", AvatarVariant.FEMININE),
            ("anime-b.glb", AvatarVariant.MASCULINE),
            ("anime-n.glb", AvatarVariant.NEUTRAL),
            ("anime_girl.glb", AvatarVariant.FEMININE),
            ("anime_boy.glb", AvatarVariant.MASCULINE),
            ("avatar-f.glb", AvatarVariant.FEMININE),
            ("avatar-m.glb", AvatarVariant.MASCULINE),
            ("hero.glb", AvatarVariant.UNSPECIFIED),
        ],
    )
    def test_infers_variant(self, library, filename, variant):
        library.root.mkdir(parents=True)
        write_glb(library.root / filename, GLTF_DOC)
        assert library.scan()[0].variant is variant

    def test_only_the_trailing_token_counts(self, library):
        """'boyd-model' must not read as masculine."""
        library.root.mkdir(parents=True)
        write_glb(library.root / "boyd-model.glb", GLTF_DOC)
        assert library.scan()[0].variant is AvatarVariant.UNSPECIFIED

    def test_the_users_pair_is_distinguished(self, library):
        library.root.mkdir(parents=True)
        write_glb(library.root / "anime-g.glb", GLTF_DOC)
        write_glb(library.root / "anime-b.glb", GLTF_DOC)
        library.scan()

        assert len(library.by_variant(AvatarVariant.FEMININE)) == 1
        assert len(library.by_variant(AvatarVariant.MASCULINE)) == 1
        # Both are still characters, and the ids stay clean.
        assert {m.id for m in library.all()} == {"anime-g", "anime-b"}
        assert all(m.kind is AvatarKind.CHARACTER for m in library.all())

    def test_summary_counts_variants(self, library):
        library.root.mkdir(parents=True)
        write_glb(library.root / "anime-g.glb", GLTF_DOC)
        write_glb(library.root / "anime-b.glb", GLTF_DOC)
        library.scan()
        assert library.summary()["by_variant"] == {"feminine": 1, "masculine": 1}


class TestAvatarApi:
    @pytest.fixture
    def client(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as c:
            yield c

    def test_starts_empty(self, client):
        assert client.get("/api/v1/avatars").json()["data"]["count"] == 0

    def test_reports_supported_formats(self, client):
        data = client.get("/api/v1/avatars/formats").json()["data"]
        assert data["recommended"] == "glb"
        assert set(data["recognised"]) == {f.lstrip(".") for f in RECOGNISED}
        assert "fbx" in data["notes"]

    def test_upload_and_inspect(self, client):
        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("hero.obj", MINIMAL_OBJ.encode(), "text/plain")},
        )
        assert response.status_code == 200
        model = response.json()["data"]["model"]
        assert model["vertices"] == 4 and model["triangles"] == 2

    def test_rejects_an_unsupported_type(self, client):
        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("virus.exe", b"MZ\x90", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "unsupported" in response.json()["error"]

    def test_upload_then_activate(self, client):
        uploaded = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("hero.obj", MINIMAL_OBJ.encode(), "text/plain")},
        ).json()["data"]["model"]

        assert client.post(f"/api/v1/avatars/active?model_id={uploaded['id']}").status_code == 200
        active = client.get("/api/v1/avatars/active").json()["data"]["active"]
        assert active["id"] == uploaded["id"]

    def test_serves_the_raw_file(self, client):
        uploaded = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("hero.obj", MINIMAL_OBJ.encode(), "text/plain")},
        ).json()["data"]["model"]
        response = client.get(f"/api/v1/avatars/{uploaded['id']}/file")
        assert response.status_code == 200
        assert b"v 0 0 0" in response.content

    def test_delete(self, client):
        uploaded = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("hero.obj", MINIMAL_OBJ.encode(), "text/plain")},
        ).json()["data"]["model"]
        assert client.delete(f"/api/v1/avatars/{uploaded['id']}").status_code == 200
        assert client.get("/api/v1/avatars").json()["data"]["count"] == 0

    def test_scan_picks_up_new_files(self, client, config):
        from pathlib import Path

        root = Path(config.system.storage).expanduser() / "avatars"
        root.mkdir(parents=True, exist_ok=True)
        (root / "dropped_in.obj").write_text(MINIMAL_OBJ)
        assert client.post("/api/v1/avatars/scan").json()["data"]["count"] == 1

    def test_filters_by_variant(self, client):
        for name in ("anime-g.obj", "anime-b.obj"):
            client.post(
                "/api/v1/avatars/upload",
                files={"file": (name, MINIMAL_OBJ.encode(), "text/plain")},
            )
        feminine = client.get("/api/v1/avatars?variant=feminine").json()["data"]
        assert feminine["count"] == 1
        assert feminine["avatars"][0]["id"] == "anime-g"

    def test_missing_model_is_404(self, client):
        assert client.get("/api/v1/avatars/nope").status_code == 404


class TestKernelIntegration:
    async def test_library_is_wired(self, kernel):
        assert kernel.avatars is not None

    async def test_status_reports_avatars(self, kernel):
        assert "avatars" in kernel.status()

    async def test_library_lives_under_storage(self, kernel):
        assert kernel.avatars.root.name == "avatars"
        assert str(kernel.avatars.root).startswith(str(kernel.config.storage_dir))


# --------------------------------------------------------------------------- #
# morph targets / lip-sync
# --------------------------------------------------------------------------- #
def morph_doc(target_names, *, count=2):
    """A glTF whose mesh carries morph targets with the given names."""
    document = json.loads(json.dumps(GLTF_DOC))
    document["meshes"][0]["primitives"][0]["targets"] = [
        {"POSITION": 0} for _ in range(count)
    ]
    document["meshes"][0]["name"] = "Face"
    if target_names is not None:
        document["meshes"][0]["extras"] = {"targetNames": target_names}
    return document


class TestVisemeMatching:
    """Riggers use no shared naming convention for shape keys.

    The voice engine emits six viseme shapes; each has to bind onto whatever
    the artist happened to call their morph targets.
    """

    def test_oculus_convention(self):
        bindings = match_visemes(
            ["viseme_sil", "viseme_PP", "viseme_FF", "viseme_DD", "viseme_SS", "viseme_aa"]
        )
        assert bindings["open"] == "viseme_aa"
        assert bindings["closed"] == "viseme_PP"
        assert bindings["neutral"] == "viseme_sil"

    def test_arkit_convention(self):
        bindings = match_visemes(
            ["jawOpen", "mouthClose", "mouthFunnel", "mouthPucker", "tongueOut"]
        )
        assert bindings["open"] == "jawOpen"
        assert bindings["closed"] == "mouthClose"

    def test_vrm_convention(self):
        bindings = match_visemes(["vrc.v_aa", "vrc.v_pp", "vrc.v_ff", "vrc.v_sil"])
        assert bindings["open"] == "vrc.v_aa"
        assert bindings["neutral"] == "vrc.v_sil"

    def test_single_letter_blender_keys(self):
        bindings = match_visemes(["Basis", "A", "E", "O", "M", "F"])
        assert bindings["open"] in {"A", "E", "O"}
        assert bindings["closed"] == "M"

    def test_separators_and_case_are_ignored(self):
        assert match_visemes(["Viseme AA"])["open"] == "Viseme AA"
        assert match_visemes(["VISEME_AA"])["open"] == "VISEME_AA"

    def test_a_target_is_never_claimed_twice(self):
        """Two shapes sharing one morph target would fight over it."""
        bindings = match_visemes(["viseme_aa", "viseme_pp", "viseme_ff"])
        assert len(set(bindings.values())) == len(bindings)

    def test_non_mouth_shapes_match_nothing(self):
        """Blink and brow keys must not be mistaken for mouth shapes."""
        assert match_visemes(["eyeBlinkLeft", "eyeBlinkRight", "browInnerUp"]) == {}

    def test_short_aliases_require_an_exact_match(self):
        # "a" as a substring would otherwise match "jawOpen", "hair", ...
        assert "open" not in match_visemes(["hairPhysics"])

    def test_empty_input(self):
        assert match_visemes([]) == {}


class TestMorphTargetParsing:
    def test_targets_are_read_from_extras(self, tmp_path):
        path = tmp_path / "face.gltf"
        path.write_text(json.dumps(morph_doc(["viseme_aa", "viseme_PP"])))

        data = parse_gltf(path)

        assert data["morph_targets"] == ["viseme_aa", "viseme_PP"]

    def test_unnamed_targets_get_positional_names(self, tmp_path):
        """glTF allows targets with no names; they still have to be listed."""
        path = tmp_path / "face.gltf"
        path.write_text(json.dumps(morph_doc(None)))

        data = parse_gltf(path)

        assert data["morph_targets"] == ["Face_target_0", "Face_target_1"]

    def test_a_model_without_targets_reports_an_empty_list(self, tmp_path):
        path = tmp_path / "plain.gltf"
        path.write_text(json.dumps(GLTF_DOC))

        assert parse_gltf(path)["morph_targets"] == []

    def test_obj_reports_no_targets(self, tmp_path):
        """OBJ is a static format; it cannot carry shape keys."""
        path = tmp_path / "model.obj"
        path.write_text(MINIMAL_OBJ)

        assert parse_obj(path)["morph_targets"] == []

    def test_glb_carries_targets_too(self, tmp_path):
        path = tmp_path / "face.glb"
        write_glb(path, morph_doc(["viseme_aa", "viseme_pp"]))

        assert parse_gltf(path)["morph_targets"] == ["viseme_aa", "viseme_pp"]

    def test_unusable_shape_keys_produce_a_warning(self, tmp_path):
        """Shape keys that match no viseme mean speech cannot move the mouth."""
        path = tmp_path / "face.gltf"
        path.write_text(json.dumps(morph_doc(["browUp", "eyeBlink"])))

        warnings = parse_gltf(path)["warnings"]

        assert any("lip-sync" in w for w in warnings)

    def test_usable_shape_keys_produce_no_warning(self, tmp_path):
        path = tmp_path / "face.gltf"
        path.write_text(json.dumps(morph_doc(["viseme_aa", "viseme_pp"])))

        assert not any("lip-sync" in w for w in parse_gltf(path)["warnings"])


class TestModelLipSyncReporting:
    def test_model_exposes_bindings(self, library):
        library.root.mkdir(parents=True, exist_ok=True)
        (library.root / "anime-g.gltf").write_text(
            json.dumps(morph_doc(["viseme_aa", "viseme_pp"]))
        )

        [model] = library.scan()

        assert model.has_morph_targets is True
        assert model.can_lip_sync is True
        assert model.viseme_bindings["open"] == "viseme_aa"

    def test_model_without_mouth_keys_cannot_lip_sync(self, library):
        library.root.mkdir(parents=True, exist_ok=True)
        (library.root / "anime-g.gltf").write_text(
            json.dumps(morph_doc(["eyeBlinkLeft", "browInnerUp"]))
        )

        [model] = library.scan()

        assert model.has_morph_targets is True
        # Present but unusable: the distinction the UI needs to show.
        assert model.can_lip_sync is False

    def test_lip_sync_needs_both_open_and_closed(self, library):
        """One mouth shape alone is a twitch, not speech."""
        library.root.mkdir(parents=True, exist_ok=True)
        (library.root / "anime-g.gltf").write_text(
            json.dumps(morph_doc(["jawOpen"], count=1))
        )

        [model] = library.scan()

        assert model.viseme_bindings == {"open": "jawOpen"}
        assert model.can_lip_sync is False

    def test_serialised_payload_carries_the_fields(self, library):
        library.root.mkdir(parents=True, exist_ok=True)
        (library.root / "anime-g.gltf").write_text(
            json.dumps(morph_doc(["viseme_aa", "viseme_pp"]))
        )

        [model] = library.scan()
        payload = model.to_dict()

        assert payload["can_lip_sync"] is True
        assert payload["morph_targets"] == ["viseme_aa", "viseme_pp"]
        assert payload["viseme_bindings"]["closed"] == "viseme_pp"


# --------------------------------------------------------------------------- #
# archive import
# --------------------------------------------------------------------------- #
def sketchfab_zip(path, *, inner="scene.gltf", document=None, extra=()):
    """A zip laid out the way marketplace downloads actually arrive."""
    import zipfile

    document = document if document is not None else GLTF_DOC
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(inner, json.dumps(document))
        bundle.writestr("scene.bin", b"\0" * 64)
        bundle.writestr("textures/body.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
        for name, payload in extra:
            bundle.writestr(name, payload)
    return path


class TestArchiveExtraction:
    """Sketchfab and friends hand out zips, not bare models."""

    def test_extracts_the_model_and_its_companions(self, tmp_path):
        archive = sketchfab_zip(tmp_path / "anime-g.zip")

        models = extract_archive(archive, tmp_path / "out")

        assert [m.name for m in models] == ["scene.gltf"]
        # The .bin and textures must travel with it or the glTF cannot resolve.
        assert (tmp_path / "out" / "scene.bin").is_file()
        assert (tmp_path / "out" / "textures" / "body.png").is_file()

    def test_drops_files_the_loader_cannot_use(self, tmp_path):
        archive = sketchfab_zip(
            tmp_path / "m.zip",
            extra=[("license.txt", "CC-BY"), ("__MACOSX/._scene.gltf", b"junk")],
        )

        extract_archive(archive, tmp_path / "out")

        written = {p.name for p in (tmp_path / "out").rglob("*") if p.is_file()}
        assert "license.txt" not in written
        assert "._scene.gltf" not in written

    def test_rejects_an_archive_with_no_model(self, tmp_path):
        import zipfile

        archive = tmp_path / "empty.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("readme.txt", "nothing here")

        with pytest.raises(ValidationError, match="no model file"):
            extract_archive(archive, tmp_path / "out")

    def test_rejects_a_non_archive(self, tmp_path):
        path = tmp_path / "not.zip"
        path.write_bytes(b"definitely not a zip")

        with pytest.raises(ValidationError, match="not a valid zip"):
            extract_archive(path, tmp_path / "out")

    def test_refuses_path_traversal(self, tmp_path):
        """Zip-slip: an entry must not be able to write outside the target."""
        import zipfile

        archive = tmp_path / "evil.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../../escaped.gltf", "{}")

        with pytest.raises(ValidationError, match="escapes"):
            extract_archive(archive, tmp_path / "out")

        assert not (tmp_path.parent / "escaped.gltf").exists()

    def test_caps_the_uncompressed_size(self, tmp_path, monkeypatch):
        """A zip bomb must not be allowed to fill the disk."""
        import zipfile

        from aera.hologram import loader as loader_module

        archive = tmp_path / "bomb.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("scene.gltf", "{}" + " " * 100_000)
        monkeypatch.setattr(loader_module, "MAX_MODEL_BYTES", 1000)

        with pytest.raises(ValidationError, match="expands to more than"):
            extract_archive(archive, tmp_path / "out")


class TestArchiveScanning:
    def test_a_dropped_zip_is_unpacked_on_scan(self, library):
        library.root.mkdir(parents=True, exist_ok=True)
        sketchfab_zip(library.root / "anime-g.zip")

        models = library.scan()

        assert len(models) == 1
        # The archive is consumed once unpacked.
        assert not (library.root / "anime-g.zip").exists()

    def test_the_folder_names_the_model_when_the_file_is_generic(self, library):
        """Sketchfab bundles are always scene.gltf; the zip carries the name."""
        library.root.mkdir(parents=True, exist_ok=True)
        sketchfab_zip(library.root / "anime-g.zip")

        [model] = library.scan()

        assert model.variant is AvatarVariant.FEMININE
        assert model.kind is AvatarKind.CHARACTER
        assert model.name == "anime g"

    def test_a_specific_filename_still_wins(self, library):
        """Only generic exporter names defer to the folder."""
        library.root.mkdir(parents=True, exist_ok=True)
        sketchfab_zip(library.root / "bundle.zip", inner="nanally-b.gltf")

        [model] = library.scan()

        assert model.variant is AvatarVariant.MASCULINE

    def test_a_corrupt_zip_does_not_stop_the_scan(self, library):
        library.root.mkdir(parents=True, exist_ok=True)
        (library.root / "broken.zip").write_bytes(b"not a zip")
        sketchfab_zip(library.root / "anime-g.zip")

        models = library.scan()

        assert len(models) == 1
        # A zip that could not be read is left in place rather than deleted.
        assert (library.root / "broken.zip").exists()


# --------------------------------------------------------------------------- #
# upload surface
# --------------------------------------------------------------------------- #
class TestUploadEndpoint:
    """What a user can actually get into the library over HTTP."""

    @pytest.fixture
    def client(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as c:
            yield c

    def test_formats_advertises_archives(self, client):
        data = client.get("/api/v1/avatars/formats").json()["data"]

        assert "zip" in data["archives"]
        # Companion files must be listed or a .bin upload looks unsupported.
        assert "bin" in data["companions"]

    def test_uploads_a_model(self, client, tmp_path):
        payload = json.dumps(GLTF_DOC).encode()

        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("anime-g.gltf", payload, "model/gltf+json")},
        )

        assert response.status_code == 200
        assert response.json()["data"]["model"]["variant"] == "feminine"

    def test_uploads_and_unpacks_an_archive(self, client, tmp_path):
        archive = sketchfab_zip(tmp_path / "anime-g.zip")

        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("anime-g.zip", archive.read_bytes(), "application/zip")},
        )

        data = response.json()["data"]
        assert data["extracted"] == ["anime-g/scene.gltf"]
        # The folder names the model, since scene.gltf says nothing.
        assert data["model"]["variant"] == "feminine"

    def test_rejects_an_unsupported_type(self, client):
        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 400
        assert "unsupported" in response.json()["error"]

    def test_oversized_uploads_are_refused_without_leaving_a_partial(
        self, client, monkeypatch
    ):
        """The stream is capped mid-write, so the partial file must be removed."""
        from aera.api.routers import avatars as router

        monkeypatch.setattr(router, "MAX_UPLOAD_BYTES", 4096)

        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("big.glb", b"\0" * 200_000, "model/gltf-binary")},
        )

        assert response.status_code == 400
        assert "4 kB" in response.json()["error"], "size must read sensibly, not '0 MB'"
        assert client.get("/api/v1/avatars").json()["data"]["count"] == 0

    def test_companion_files_are_accepted(self, client):
        """A .gltf needs its .bin; rejecting it would break the model."""
        response = client.post(
            "/api/v1/avatars/upload",
            files={"file": ("scene.bin", b"\0" * 64, "application/octet-stream")},
        )

        assert response.status_code == 200
