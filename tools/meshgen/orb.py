"""Voice orb generator.

Builds the AERA presence orb: a subdivided icosphere with layered noise
displacement, an equatorial energy ring and an inner core shell. Spherical UVs
are laid out so a 4K texture wraps cleanly.

Resolution is expressed as an *edge length in millimetres* rather than a
subdivision count, so `--detail 0.5` means "half-millimetre triangles" and the
vertex budget follows from the requested size.
"""

from __future__ import annotations

import math

from .obj import Material, Mesh, Vec3

# Golden-ratio icosahedron: the standard seed for a uniform sphere.
_PHI = (1.0 + math.sqrt(5.0)) / 2.0

_ICO_VERTS: tuple[Vec3, ...] = (
    (-1, _PHI, 0), (1, _PHI, 0), (-1, -_PHI, 0), (1, -_PHI, 0),
    (0, -1, _PHI), (0, 1, _PHI), (0, -1, -_PHI), (0, 1, -_PHI),
    (_PHI, 0, -1), (_PHI, 0, 1), (-_PHI, 0, -1), (-_PHI, 0, 1),
)

_ICO_FACES: tuple[tuple[int, int, int], ...] = (
    (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
    (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
    (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
    (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
)


def _normalise(v: Vec3) -> Vec3:
    x, y, z = v
    length = math.sqrt(x * x + y * y + z * z)
    return (x / length, y / length, z / length) if length else (0.0, 1.0, 0.0)


def _hash_noise(x: float, y: float, z: float, seed: int) -> float:
    """Cheap deterministic value noise in [-1, 1].

    Trigonometric hashing avoids a dependency while staying stable across runs,
    which matters because the same seed must reproduce the same asset.
    """
    n = math.sin(x * 12.9898 + y * 78.233 + z * 37.719 + seed * 4.1414) * 43758.5453
    return 2.0 * (n - math.floor(n)) - 1.0


def _fbm(v: Vec3, *, octaves: int, seed: int) -> float:
    """Fractal noise: octaves of value noise at doubling frequency."""
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for i in range(octaves):
        total += amplitude * _hash_noise(
            v[0] * frequency, v[1] * frequency, v[2] * frequency, seed + i
        )
        norm += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return total / norm if norm else 0.0


def subdivisions_for(diameter_mm: float, edge_mm: float) -> int:
    """Subdivision level giving roughly the requested triangle edge length.

    An icosphere at level n has 20·4ⁿ triangles; edge length scales as 2⁻ⁿ from
    the base icosahedron edge. Capped at 7 (≈327k triangles) because beyond
    that the file stops being loadable in real tools.
    """
    radius = diameter_mm / 2.0
    base_edge = radius / math.sin(2 * math.pi / 5)  # icosahedron edge for this radius
    if edge_mm <= 0:
        return 4
    level = math.log2(base_edge / edge_mm)
    return max(0, min(7, math.ceil(level)))


def icosphere(radius: float, subdivisions: int) -> tuple[list[Vec3], list[tuple[int, int, int]]]:
    """Subdivided icosahedron projected onto a sphere."""
    verts: list[Vec3] = [
        tuple(c * radius for c in _normalise(v)) for v in _ICO_VERTS  # type: ignore[misc]
    ]
    faces: list[tuple[int, int, int]] = list(_ICO_FACES)

    def _midpoint(
        a: int,
        b: int,
        cache: dict[tuple[int, int], int],
        points: list[Vec3],
    ) -> int:
        """Index of the vertex between a and b, created once and reused."""
        key = (min(a, b), max(a, b))
        cached = cache.get(key)
        if cached is not None:
            return cached
        va, vb = points[a], points[b]
        mid = _normalise(((va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2, (va[2] + vb[2]) / 2))
        points.append(tuple(c * radius for c in mid))  # type: ignore[arg-type]
        cache[key] = len(points) - 1
        return cache[key]

    for _ in range(subdivisions):
        midpoints: dict[tuple[int, int], int] = {}
        new_faces: list[tuple[int, int, int]] = []

        for a, b, c in faces:
            ab = _midpoint(a, b, midpoints, verts)
            bc = _midpoint(b, c, midpoints, verts)
            ca = _midpoint(c, a, midpoints, verts)
            new_faces.extend([(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)])
        faces = new_faces

    return verts, faces


def _spherical_uv(v: Vec3) -> tuple[float, float]:
    n = _normalise(v)
    u = 0.5 + math.atan2(n[2], n[0]) / (2 * math.pi)
    y = 0.5 - math.asin(max(-1.0, min(1.0, n[1]))) / math.pi
    return (u, y)


def build_orb(
    *,
    diameter_mm: float = 60.0,
    edge_mm: float = 0.5,
    displacement: float = 0.035,
    octaves: int = 4,
    seed: int = 7,
    rings: bool = True,
) -> Mesh:
    """Generate the voice orb.

    ``displacement`` is a fraction of the radius, giving the surface its
    energy-shell irregularity rather than a billiard-ball finish.
    """
    radius = diameter_mm / 2.0
    level = subdivisions_for(diameter_mm, edge_mm)
    verts, faces = icosphere(radius, level)

    mesh = Mesh(name="AERA_VoiceOrb", material="orb_core")

    for v in verts:
        direction = _normalise(v)
        offset = 1.0 + displacement * _fbm(
            (direction[0] * 3.0, direction[1] * 3.0, direction[2] * 3.0),
            octaves=octaves,
            seed=seed,
        )
        position = tuple(c * offset for c in v)
        mesh.add_vertex(position, normal=direction, uv=_spherical_uv(direction))  # type: ignore[arg-type]

    for a, b, c in faces:
        mesh.add_triangle(a, b, c)

    if rings:
        mesh.merge(_energy_ring(radius * 1.28, thickness=radius * 0.018, segments=256, tilt=0.0))
        mesh.merge(_energy_ring(radius * 1.42, thickness=radius * 0.012, segments=256, tilt=0.42))
        mesh.merge(_energy_ring(radius * 1.16, thickness=radius * 0.010, segments=256, tilt=-0.68))

    mesh.recompute_normals()
    return mesh


def _energy_ring(radius: float, *, thickness: float, segments: int, tilt: float) -> Mesh:
    """A torus in the XZ plane, rotated about X by ``tilt`` radians."""
    ring = Mesh(name="ring", material="orb_ring")
    minor_segments = max(6, segments // 24)

    cos_t, sin_t = math.cos(tilt), math.sin(tilt)

    for i in range(segments):
        theta = 2 * math.pi * i / segments
        cx, cz = math.cos(theta), math.sin(theta)
        for j in range(minor_segments):
            phi = 2 * math.pi * j / minor_segments
            r = radius + thickness * math.cos(phi)
            x = r * cx
            y = thickness * math.sin(phi)
            z = r * cz
            # Rotate about the X axis.
            ry = y * cos_t - z * sin_t
            rz = y * sin_t + z * cos_t
            normal = _normalise((math.cos(phi) * cx, math.sin(phi), math.cos(phi) * cz))
            ring.add_vertex(
                (x, ry, rz),
                normal=normal,
                uv=(i / segments, j / minor_segments),
            )

    for i in range(segments):
        for j in range(minor_segments):
            a = i * minor_segments + j
            b = ((i + 1) % segments) * minor_segments + j
            c = ((i + 1) % segments) * minor_segments + (j + 1) % minor_segments
            d = i * minor_segments + (j + 1) % minor_segments
            ring.add_quad(a, b, c, d)

    return ring


def orb_materials() -> list[Material]:
    """Emissive materials referencing the 4K texture set."""
    return [
        Material(
            name="orb_core",
            diffuse=(0.30, 0.65, 1.00),
            specular=(0.9, 0.95, 1.0),
            emissive=(0.18, 0.42, 0.85),
            shininess=180.0,
            opacity=0.92,
            diffuse_map="textures/orb_core_diffuse_4k.png",
            normal_map="textures/orb_core_normal_4k.png",
            roughness_map="textures/orb_core_roughness_4k.png",
        ),
        Material(
            name="orb_ring",
            diffuse=(0.49, 0.36, 1.00),
            specular=(1.0, 1.0, 1.0),
            emissive=(0.35, 0.25, 0.90),
            shininess=220.0,
            opacity=0.75,
        ),
    ]
