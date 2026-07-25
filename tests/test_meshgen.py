"""Tests for the hologram mesh generator.

The contract: generated OBJ files must be geometrically valid and loadable.
A mesh with out-of-range indices or degenerate faces will crash a real
renderer, so those are hard failures here.
"""

from __future__ import annotations

import math

import pytest

from tools.meshgen.character import FEMININE, MASCULINE, build_character, character_materials
from tools.meshgen.detail import AnatomyField, apply_anatomy, apply_microdetail
from tools.meshgen.obj import Material, Mesh, write_mtl
from tools.meshgen.orb import build_orb, icosphere, orb_materials, subdivisions_for


def parse_obj(text: str) -> dict:
    """Parse OBJ text back into counts and indices for validation."""
    verts, uvs, normals, faces = [], [], [], []
    for line in text.splitlines():
        if line.startswith("v "):
            verts.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith("vt "):
            uvs.append(tuple(map(float, line.split()[1:3])))
        elif line.startswith("vn "):
            normals.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith("f "):
            faces.append([tuple(p.split("/")) for p in line.split()[1:]])
    return {"v": verts, "vt": uvs, "vn": normals, "f": faces}


class TestObjWriter:
    def test_round_trip(self):
        mesh = Mesh(name="tri")
        a = mesh.add_vertex((0, 0, 0), normal=(0, 1, 0), uv=(0, 0))
        b = mesh.add_vertex((1, 0, 0), normal=(0, 1, 0), uv=(1, 0))
        c = mesh.add_vertex((0, 1, 0), normal=(0, 1, 0), uv=(0, 1))
        mesh.add_triangle(a, b, c)

        parsed = parse_obj(mesh.to_obj())
        assert len(parsed["v"]) == 3
        assert len(parsed["f"]) == 1

    def test_obj_indices_are_one_based(self):
        """OBJ is 1-indexed; an off-by-one here silently corrupts every mesh."""
        mesh = Mesh()
        mesh.add_vertex((0, 0, 0), normal=(0, 1, 0), uv=(0, 0))
        mesh.add_vertex((1, 0, 0), normal=(0, 1, 0), uv=(1, 0))
        mesh.add_vertex((0, 1, 0), normal=(0, 1, 0), uv=(0, 1))
        mesh.add_triangle(0, 1, 2)
        assert "f 1/1/1 2/2/2 3/3/3" in mesh.to_obj()

    def test_quad_becomes_two_triangles(self):
        mesh = Mesh()
        for p in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)):
            mesh.add_vertex(p)
        mesh.add_quad(0, 1, 2, 3)
        assert mesh.triangle_count == 2

    def test_merge_offsets_indices(self):
        a = Mesh()
        for p in ((0, 0, 0), (1, 0, 0), (0, 1, 0)):
            a.add_vertex(p)
        a.add_triangle(0, 1, 2)

        b = Mesh()
        for p in ((2, 0, 0), (3, 0, 0), (2, 1, 0)):
            b.add_vertex(p)
        b.add_triangle(0, 1, 2)

        a.merge(b)
        assert len(a.vertices) == 6
        # The merged face must reference the offset range, not the original.
        assert a.faces[1][0][0] == 3

    def test_normals_are_unit_length(self):
        mesh = build_orb(diameter_mm=20, edge_mm=4)
        for nx, ny, nz in mesh.normals:
            assert abs(math.sqrt(nx * nx + ny * ny + nz * nz) - 1.0) < 1e-6

    def test_scale_to_height(self):
        mesh = build_character(FEMININE, name="t", segments=12)
        mesh.scale_to_height(1000.0)
        assert abs(mesh.dimensions()[1] - 1000.0) < 0.5

    def test_mtl_output(self, tmp_path):
        path = write_mtl(tmp_path / "m.mtl", [Material(name="skin", diffuse_map="d.png")])
        body = path.read_text()
        assert "newmtl skin" in body and "map_Kd d.png" in body


class TestOrb:
    def test_icosphere_grows_by_four(self):
        for level in range(4):
            _, faces = icosphere(1.0, level)
            assert len(faces) == 20 * (4**level)

    def test_icosphere_points_lie_on_the_sphere(self):
        verts, _ = icosphere(5.0, 3)
        for x, y, z in verts:
            assert abs(math.sqrt(x * x + y * y + z * z) - 5.0) < 1e-9

    def test_subdivision_scales_with_requested_detail(self):
        coarse = subdivisions_for(60.0, 4.0)
        fine = subdivisions_for(60.0, 0.25)
        assert fine > coarse

    def test_subdivision_is_capped(self):
        """An absurd request must clamp rather than attempt terabytes."""
        assert subdivisions_for(1600.0, 0.01) <= 7

    def test_builds_with_rings(self):
        with_rings = build_orb(diameter_mm=60, edge_mm=3, rings=True)
        without = build_orb(diameter_mm=60, edge_mm=3, rings=False)
        assert with_rings.triangle_count > without.triangle_count

    def test_displacement_is_deterministic(self):
        a = build_orb(diameter_mm=60, edge_mm=3, seed=42)
        b = build_orb(diameter_mm=60, edge_mm=3, seed=42)
        assert a.vertices == b.vertices

    def test_different_seeds_differ(self):
        a = build_orb(diameter_mm=60, edge_mm=3, seed=1)
        b = build_orb(diameter_mm=60, edge_mm=3, seed=2)
        assert a.vertices != b.vertices

    def test_uvs_are_normalised(self):
        mesh = build_orb(diameter_mm=60, edge_mm=3)
        for u, v in mesh.uvs:
            assert -0.001 <= u <= 1.001 and -0.001 <= v <= 1.001

    def test_materials_reference_4k_textures(self):
        body = "\n".join(m.to_mtl() for m in orb_materials())
        assert "_4k.png" in body


class TestCharacter:
    @pytest.mark.parametrize("proportions", [FEMININE, MASCULINE])
    def test_height_matches_the_specification(self, proportions):
        mesh = build_character(proportions, name="t", segments=24)
        assert abs(mesh.dimensions()[1] - proportions.height) < proportions.height * 0.03

    def test_builds_differ(self):
        girl = build_character(FEMININE, name="g", segments=24)
        boy = build_character(MASCULINE, name="b", segments=24)
        # The masculine build is taller and broader at the shoulder.
        assert boy.dimensions()[1] > girl.dimensions()[1]
        assert boy.dimensions()[0] > girl.dimensions()[0]

    def test_anime_head_ratio(self):
        """Anime proportions: a larger head than realistic anatomy."""
        assert FEMININE.head_ratio < 7.0
        assert FEMININE.head_length == pytest.approx(FEMININE.height / FEMININE.head_ratio)

    @pytest.mark.parametrize("proportions", [FEMININE, MASCULINE])
    def test_geometry_is_valid(self, proportions):
        """No out-of-range or degenerate faces: these crash real renderers."""
        mesh = build_character(proportions, name="t", segments=24)
        count = len(mesh.vertices)
        for face in mesh.faces:
            indices = [v for v, _, _ in face]
            assert all(0 <= i < count for i in indices), "vertex index out of range"
            assert len(set(indices)) == 3, "degenerate triangle"

    @pytest.mark.parametrize("proportions", [FEMININE, MASCULINE])
    def test_every_vertex_has_a_normal(self, proportions):
        mesh = build_character(proportions, name="t", segments=24)
        assert len(mesh.normals) == len(mesh.vertices)

    def test_limbs_are_attached_to_the_body(self):
        """Regression: arms once floated detached from the shoulder."""
        mesh = build_character(MASCULINE, name="t", segments=32)
        h = MASCULINE.height
        shoulder_band = [v for v in mesh.vertices if h * 0.76 < v[1] < h * 0.80]
        assert shoulder_band, "no geometry at shoulder height"

        # Torso and arm geometry must overlap in X, not leave a gap.
        xs = sorted(v[0] for v in shoulder_band)
        gaps = [b - a for a, b in zip(xs, xs[1:], strict=False)]
        assert max(gaps) < h * 0.04, "gap between the torso and arm at the shoulder"

    def test_feet_reach_the_ground(self):
        mesh = build_character(FEMININE, name="t", segments=24)
        assert mesh.bounds()[0][1] < FEMININE.height * 0.02

    def test_materials_name_the_expected_slots(self):
        names = {m.name for m in character_materials(hair=(0, 0, 0), accent=(1, 1, 1), prefix="x")}
        assert names == {"skin", "hair", "accent"}


class TestDetail:
    """Detail passes must add information, not just polygons."""

    def test_anatomy_displaces_the_surface(self):
        flat = build_character(MASCULINE, name="f", segments=32, anatomy=0.0)
        shaped = build_character(MASCULINE, name="s", segments=32, anatomy=1.0)
        moved = [
            math.dist(a, b)
            for a, b in zip(flat.vertices, shaped.vertices, strict=True)
        ]
        assert max(moved) > 0
        # Relief must be visible: at least 1% of height, or it reads as flat.
        assert max(moved) / MASCULINE.height > 0.01

    def test_anatomy_relief_stays_plausible(self):
        """Displacement must not balloon the silhouette."""
        shaped = build_character(MASCULINE, name="s", segments=32, anatomy=1.0)
        flat = build_character(MASCULINE, name="f", segments=32, anatomy=0.0)
        growth = shaped.dimensions()[0] / flat.dimensions()[0]
        assert 1.0 <= growth < 1.20, f"silhouette grew {growth:.2f}x"

    def test_masculine_definition_exceeds_feminine(self):
        def relief(p):
            flat = build_character(p, name="f", segments=32, anatomy=0.0)
            shaped = build_character(p, name="s", segments=32, anatomy=1.0)
            moved = [
                math.dist(a, b)
                for a, b in zip(flat.vertices, shaped.vertices, strict=True)
            ]
            return max(moved) / p.height

        assert relief(MASCULINE) > relief(FEMININE)

    def test_anatomy_is_deterministic(self):
        a = build_character(FEMININE, name="a", segments=24, anatomy=1.0)
        b = build_character(FEMININE, name="b", segments=24, anatomy=1.0)
        assert a.vertices == b.vertices

    def test_microdetail_perturbs_every_vertex(self):
        plain = build_character(FEMININE, name="p", segments=24)
        rough = build_character(FEMININE, name="r", segments=24, microdetail=0.5)
        moved = sum(
            1
            for a, b in zip(plain.vertices, rough.vertices, strict=True)
            if math.dist(a, b) > 1e-6
        )
        assert moved > len(plain.vertices) * 0.9

    def test_microdetail_amplitude_is_respected(self):
        plain = build_character(FEMININE, name="p", segments=24)
        rough = build_character(FEMININE, name="r", segments=24, microdetail=0.4)
        worst = max(
            math.dist(a, b)
            for a, b in zip(plain.vertices, rough.vertices, strict=True)
        )
        assert worst <= 0.45, "microdetail exceeded its requested amplitude"

    def test_detail_preserves_valid_geometry(self):
        mesh = build_character(MASCULINE, name="d", segments=32, anatomy=1.0, microdetail=0.3)
        count = len(mesh.vertices)
        for face in mesh.faces:
            indices = [v for v, _, _ in face]
            assert all(0 <= i < count for i in indices)
            assert len(set(indices)) == 3

    def test_anatomy_field_is_zero_far_from_landmarks(self):
        field = AnatomyField(1700.0, 200.0, 150.0, masculine=True)
        assert field.sample((9999.0, 9999.0, 9999.0)) == 0.0

    def test_passes_are_composable(self):
        mesh = build_character(FEMININE, name="c", segments=24)
        before = len(mesh.vertices)
        apply_anatomy(mesh, height=FEMININE.height, shoulder_x=180, hip_x=160, masculine=False)
        apply_microdetail(mesh, scale=0.05, amplitude=0.2)
        # Displacement must never change topology.
        assert len(mesh.vertices) == before


class TestTargetSize:
    """--target-mb solves for a segment count near a requested file size."""

    def test_solver_hits_the_target(self):
        from tools.meshgen.__main__ import segments_for_target

        # 6 MB needs ~170 segments, so the ceiling must not cut the search off.
        target = 6 * 1_048_576
        segments = segments_for_target(
            lambda seg: build_character(FEMININE, name="p", segments=seg),
            target,
            low=16,
            high=512,
        )
        size = len(build_character(FEMININE, name="m", segments=segments).to_obj().encode())
        assert abs(size - target) / target < 0.10, (
            f"{segments} segments gave {size / 1_048_576:.2f} MB, wanted 6 MB"
        )

    def test_larger_target_yields_more_segments(self):
        from tools.meshgen.__main__ import segments_for_target

        def build(seg):
            return build_character(FEMININE, name="p", segments=seg)

        small = segments_for_target(build, 2 * 1_048_576, low=16, high=512)
        large = segments_for_target(build, 8 * 1_048_576, low=16, high=512)
        assert large > small

    def test_solver_respects_the_ceiling(self):
        from tools.meshgen.__main__ import segments_for_target

        # An unreachable target must clamp rather than run away.
        segments = segments_for_target(
            lambda seg: build_character(FEMININE, name="p", segments=seg),
            10**12,
            low=16,
            high=64,
        )
        assert segments <= 64


class TestCli:
    def test_generates_every_asset(self, tmp_path):
        from tools.meshgen.__main__ import main

        assert main(["--out", str(tmp_path), "--detail", "3", "--segments", "16"]) == 0
        for name in ("voice_orb", "anime_girl", "anime_boy"):
            assert (tmp_path / f"{name}.obj").is_file()
            assert (tmp_path / f"{name}.mtl").is_file()

    def test_target_mb_flag(self, tmp_path):
        from tools.meshgen.__main__ import main

        main(["--out", str(tmp_path), "--only", "girl", "--target-mb", "5"])
        mb = (tmp_path / "anime_girl.obj").stat().st_size / 1_048_576
        assert 3.0 < mb < 8.0, f"target 5 MB produced {mb:.1f} MB"

    def test_detail_flags(self, tmp_path):
        from tools.meshgen.__main__ import main

        main([
            "--out", str(tmp_path), "--only", "boy", "--segments", "24",
            "--anatomy", "1.0", "--microdetail", "0.3",
        ])
        assert (tmp_path / "anime_boy.obj").is_file()

    def test_single_asset(self, tmp_path):
        from tools.meshgen.__main__ import main

        main(["--out", str(tmp_path), "--only", "orb", "--detail", "4"])
        assert (tmp_path / "voice_orb.obj").is_file()
        assert not (tmp_path / "anime_girl.obj").exists()

    def test_impossible_detail_is_clamped(self, tmp_path, capsys):
        """0.01 mm must warn and clamp rather than attempt 1.7 TB."""
        from tools.meshgen.__main__ import MIN_EDGE_MM, main

        main(["--out", str(tmp_path), "--only", "orb", "--detail", "0.01"])
        assert "clamping" in capsys.readouterr().err
        size_mb = (tmp_path / "voice_orb.obj").stat().st_size / 1_048_576
        assert size_mb < 500, "clamp failed; file is unusably large"
        assert MIN_EDGE_MM > 0.01
