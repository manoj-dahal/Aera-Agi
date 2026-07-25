"""Minimal OBJ/MTL writer.

Emits Wavefront OBJ with vertex normals and UV coordinates, so the meshes can
carry 4K texture maps. Deliberately dependency-free: mesh generation must work
in a bare Python environment.

Units are millimetres throughout, matching the convention used by the AERA
hologram assets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

Vec3 = tuple[float, float, float]
Vec2 = tuple[float, float]


@dataclass
class Mesh:
    """An indexed triangle mesh with optional normals and UVs."""

    name: str = "mesh"
    vertices: list[Vec3] = field(default_factory=list)
    normals: list[Vec3] = field(default_factory=list)
    uvs: list[Vec2] = field(default_factory=list)
    #: Triangles as (vertex, uv, normal) index triples, zero-based.
    faces: list[tuple[tuple[int, int, int], ...]] = field(default_factory=list)
    material: str | None = None

    # ------------------------------------------------------------------ #
    # construction
    # ------------------------------------------------------------------ #
    def add_vertex(self, position: Vec3, normal: Vec3 | None = None, uv: Vec2 | None = None) -> int:
        """Append a vertex, returning its index."""
        self.vertices.append(position)
        if normal is not None:
            self.normals.append(normal)
        if uv is not None:
            self.uvs.append(uv)
        return len(self.vertices) - 1

    def add_triangle(self, a: int, b: int, c: int) -> None:
        """Add a triangle whose vertex, uv and normal indices coincide."""
        self.faces.append(((a, a, a), (b, b, b), (c, c, c)))

    def add_quad(self, a: int, b: int, c: int, d: int) -> None:
        """Add a quad as two triangles, wound consistently."""
        self.add_triangle(a, b, c)
        self.add_triangle(a, c, d)

    def merge(self, other: Mesh) -> None:
        """Append another mesh, offsetting its indices."""
        v_off = len(self.vertices)
        n_off = len(self.normals)
        t_off = len(self.uvs)
        self.vertices.extend(other.vertices)
        self.normals.extend(other.normals)
        self.uvs.extend(other.uvs)
        for face in other.faces:
            self.faces.append(
                tuple((v + v_off, t + t_off, n + n_off) for v, t, n in face)
            )

    # ------------------------------------------------------------------ #
    # geometry helpers
    # ------------------------------------------------------------------ #
    @property
    def triangle_count(self) -> int:
        return len(self.faces)

    def bounds(self) -> tuple[Vec3, Vec3]:
        """Axis-aligned bounding box as (min, max)."""
        if not self.vertices:
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
        xs, ys, zs = zip(*self.vertices, strict=True)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def dimensions(self) -> Vec3:
        low, high = self.bounds()
        return (high[0] - low[0], high[1] - low[1], high[2] - low[2])

    def recompute_normals(self) -> None:
        """Area-weighted smooth normals, one per vertex."""
        accum: list[list[float]] = [[0.0, 0.0, 0.0] for _ in self.vertices]

        for face in self.faces:
            ia, ib, ic = face[0][0], face[1][0], face[2][0]
            a, b, c = self.vertices[ia], self.vertices[ib], self.vertices[ic]
            # Cross product magnitude is proportional to triangle area, which
            # weights each contribution correctly without extra work.
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            for index in (ia, ib, ic):
                accum[index][0] += nx
                accum[index][1] += ny
                accum[index][2] += nz

        self.normals = []
        for nx, ny, nz in accum:
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            if length < 1e-12:
                self.normals.append((0.0, 1.0, 0.0))
            else:
                self.normals.append((nx / length, ny / length, nz / length))

        # Normal indices now match vertex indices.
        self.faces = [tuple((v, t, v) for v, t, _ in face) for face in self.faces]

    def translate(self, dx: float, dy: float, dz: float) -> None:
        self.vertices = [(x + dx, y + dy, z + dz) for x, y, z in self.vertices]

    def scale_to_height(self, height_mm: float) -> None:
        """Uniformly scale so the Y extent equals ``height_mm``."""
        current = self.dimensions()[1]
        if current <= 0:
            return
        factor = height_mm / current
        self.vertices = [(x * factor, y * factor, z * factor) for x, y, z in self.vertices]

    # ------------------------------------------------------------------ #
    # output
    # ------------------------------------------------------------------ #
    def to_obj(self, *, mtllib: str | None = None) -> str:
        """Serialise to Wavefront OBJ text."""
        out: list[str] = [
            "# Generated by AERA meshgen",
            f"# {self.name}",
            f"# vertices: {len(self.vertices)}  triangles: {len(self.faces)}",
            "# units: millimetres",
        ]
        if mtllib:
            out.append(f"mtllib {mtllib}")
        out.append(f"o {self.name}")

        for x, y, z in self.vertices:
            out.append(f"v {x:.5f} {y:.5f} {z:.5f}")
        for u, v in self.uvs:
            out.append(f"vt {u:.6f} {v:.6f}")
        for x, y, z in self.normals:
            out.append(f"vn {x:.5f} {y:.5f} {z:.5f}")

        if self.material:
            out.append(f"usemtl {self.material}")
        out.append("s 1")

        has_uv = bool(self.uvs)
        has_n = bool(self.normals)
        for face in self.faces:
            parts = []
            for v, t, n in face:
                if has_uv and has_n:
                    parts.append(f"{v + 1}/{t + 1}/{n + 1}")
                elif has_n:
                    parts.append(f"{v + 1}//{n + 1}")
                elif has_uv:
                    parts.append(f"{v + 1}/{t + 1}")
                else:
                    parts.append(str(v + 1))
            out.append("f " + " ".join(parts))

        return "\n".join(out) + "\n"

    def save(self, path: str | Path, *, mtllib: str | None = None) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_obj(mtllib=mtllib), encoding="utf-8")
        return target


@dataclass
class Material:
    """A PBR-ish MTL entry pointing at 4K texture maps."""

    name: str
    diffuse: Vec3 = (0.8, 0.8, 0.8)
    specular: Vec3 = (0.3, 0.3, 0.3)
    emissive: Vec3 = (0.0, 0.0, 0.0)
    shininess: float = 64.0
    opacity: float = 1.0
    diffuse_map: str | None = None
    normal_map: str | None = None
    roughness_map: str | None = None

    def to_mtl(self) -> str:
        lines = [
            f"newmtl {self.name}",
            f"Kd {self.diffuse[0]:.4f} {self.diffuse[1]:.4f} {self.diffuse[2]:.4f}",
            f"Ks {self.specular[0]:.4f} {self.specular[1]:.4f} {self.specular[2]:.4f}",
            f"Ke {self.emissive[0]:.4f} {self.emissive[1]:.4f} {self.emissive[2]:.4f}",
            f"Ns {self.shininess:.2f}",
            f"d {self.opacity:.4f}",
            "illum 2",
        ]
        if self.diffuse_map:
            lines.append(f"map_Kd {self.diffuse_map}")
        if self.normal_map:
            lines.append(f"norm {self.normal_map}")
        if self.roughness_map:
            lines.append(f"map_Ns {self.roughness_map}")
        return "\n".join(lines)


def write_mtl(path: str | Path, materials: list[Material]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "# Generated by AERA meshgen\n\n" + "\n\n".join(m.to_mtl() for m in materials) + "\n"
    target.write_text(body, encoding="utf-8")
    return target
