"""Tests for the hologram mesh generator.

The contract: generated OBJ files must be geometrically valid and loadable.
A mesh with out-of-range indices or degenerate faces will crash a real
renderer, so those are hard failures here.
"""

from __future__ import annotations

import math

import pytest

from tools.meshgen.character import FEMININE, MASCULINE, build_character, character_materials
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


class TestCli:
    def test_generates_every_asset(self, tmp_path):
        from tools.meshgen.__main__ import main

        assert main(["--out", str(tmp_path), "--detail", "3", "--segments", "16"]) == 0
        for name in ("voice_orb", "anime_girl", "anime_boy"):
            assert (tmp_path / f"{name}.obj").is_file()
            assert (tmp_path / f"{name}.mtl").is_file()

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
