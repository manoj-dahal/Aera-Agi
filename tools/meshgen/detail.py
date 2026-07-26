# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Surface detail for the character meshes.

Raising polygon count alone produces smoother tubes, not a better model. This
module adds information the extra vertices can actually carry:

* **Anatomical displacement** - clavicle, sternum, spine channel, shoulder
  blades, knee caps, ankle bones. Driven by anatomical landmarks rather than
  uniform noise, so the shapes land where a body has them.
* **Pore-level microdetail** - fine fractal noise at skin scale, which is what
  makes a high-poly surface read as organic instead of moulded plastic.

Both operate on an existing mesh, displacing vertices along their normals.
"""

from __future__ import annotations

import math

from .obj import Mesh, Vec3


def _hash3(x: float, y: float, z: float, seed: int) -> float:
    """Deterministic value noise in [-1, 1]."""
    n = math.sin(x * 127.1 + y * 311.7 + z * 74.7 + seed * 3.7) * 43758.5453123
    return 2.0 * (n - math.floor(n)) - 1.0


def _fbm(p: Vec3, *, octaves: int, seed: int, lacunarity: float = 2.0) -> float:
    """Fractal Brownian motion: summed octaves at rising frequency."""
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for i in range(octaves):
        total += amplitude * _hash3(
            p[0] * frequency, p[1] * frequency, p[2] * frequency, seed + i * 17
        )
        norm += amplitude
        amplitude *= 0.5
        frequency *= lacunarity
    return total / norm if norm else 0.0


def _falloff(distance: float, radius: float) -> float:
    """Smooth 1-to-0 weight over ``radius``; zero beyond it."""
    if distance >= radius:
        return 0.0
    t = 1.0 - distance / radius
    return t * t * (3.0 - 2.0 * t)  # smoothstep


class AnatomyField:
    """Signed displacement from anatomical landmarks.

    Each landmark is a point (or mirrored pair) with a radius of influence and
    an amplitude. Positive amplitudes push outward - a knee cap, a clavicle
    ridge. Negative ones carve inward - the spine channel, the sternum notch.
    """

    def __init__(self, height: float, shoulder_x: float, hip_x: float, *, masculine: bool) -> None:
        h = height
        sx = shoulder_x
        hx = hip_x
        # Depth scale so the landmarks sit on the surface, not inside it.
        d = h * 0.05

        m = 1.35 if masculine else 0.85  # masculine builds show more definition
        # Amplitude scale. Visible anatomical relief on a human figure is
        # roughly 1-2% of total height; below that it vanishes at any sane
        # viewing distance.
        a = 3.6

        #: (position, radius, amplitude, mirrored)
        self.landmarks: list[tuple[Vec3, float, float, bool]] = [
            # -- torso, front ----------------------------------------------
            ((sx * 0.52, h * 0.790, d * 0.62), h * 0.048, h * 0.0042 * a * m, True),   # clavicle
            ((0.0, h * 0.760, d * 0.72), h * 0.040, -h * 0.0028 * a, False),            # sternal notch
            ((sx * 0.42, h * 0.720, d * 0.70), h * 0.062, h * 0.0038 * a * m, True),   # pectoral
            ((0.0, h * 0.640, d * 0.66), h * 0.055, -h * 0.0018 * a, False),            # solar plexus
            ((sx * 0.30, h * 0.600, d * 0.62), h * 0.044, h * 0.0026 * a * m, True),   # rib arch
            ((0.0, h * 0.560, d * 0.58), h * 0.030, -h * 0.0022 * a, False),            # navel
            ((sx * 0.26, h * 0.585, d * 0.55), h * 0.038, h * 0.0030 * a * m, True),   # oblique
            # -- torso, back -----------------------------------------------
            ((0.0, h * 0.700, -d * 0.62), h * 0.090, -h * 0.0034 * a, False),           # spine channel
            ((0.0, h * 0.580, -d * 0.58), h * 0.070, -h * 0.0026 * a, False),
            ((sx * 0.46, h * 0.745, -d * 0.58), h * 0.056, h * 0.0040 * a * m, True),  # scapula
            ((sx * 0.34, h * 0.680, -d * 0.56), h * 0.050, h * 0.0024 * a * m, True),  # lat
            # -- shoulders and arms ----------------------------------------
            ((sx * 0.82, h * 0.778, 0.0), h * 0.050, h * 0.0044 * a * m, True),        # deltoid crown
            ((sx * 0.90, h * 0.700, d * 0.28), h * 0.042, h * 0.0032 * a * m, True),   # bicep
            ((sx * 0.90, h * 0.700, -d * 0.30), h * 0.040, h * 0.0026 * a * m, True),  # tricep
            ((sx * 0.94, h * 0.628, 0.0), h * 0.030, h * 0.0022 * a, True),            # elbow
            ((sx * 0.96, h * 0.560, d * 0.20), h * 0.034, h * 0.0022 * a * m, True),   # forearm
            # -- hips and legs ---------------------------------------------
            ((hx * 0.88, h * 0.510, d * 0.34), h * 0.048, h * 0.0030 * a, True),       # iliac crest
            ((hx * 0.62, h * 0.470, -d * 0.44), h * 0.070, h * 0.0044 * a, True),      # glute
            ((hx * 0.66, h * 0.400, d * 0.30), h * 0.058, h * 0.0034 * a * m, True),   # quadriceps
            ((hx * 0.66, h * 0.380, -d * 0.28), h * 0.052, h * 0.0026 * a, True),      # hamstring
            ((hx * 0.60, h * 0.278, d * 0.24), h * 0.030, h * 0.0034 * a, True),       # knee cap
            ((hx * 0.60, h * 0.200, -d * 0.24), h * 0.040, h * 0.0038 * a * m, True),  # calf
            ((hx * 0.58, h * 0.055, 0.0), h * 0.022, h * 0.0020 * a, True),            # ankle
            # -- head -------------------------------------------------------
            ((0.0, h * 0.905, d * 0.52), h * 0.026, -h * 0.0016 * a, False),            # nose bridge
            ((sx * 0.16, h * 0.912, d * 0.44), h * 0.030, -h * 0.0022 * a, True),      # eye socket
            ((sx * 0.22, h * 0.895, d * 0.34), h * 0.028, h * 0.0020 * a, True),       # cheekbone
            ((0.0, h * 0.860, d * 0.42), h * 0.024, h * 0.0016 * a, False),             # chin
            ((sx * 0.20, h * 0.870, d * 0.20), h * 0.030, -h * 0.0018 * a, True),      # jaw hollow
        ]

    def sample(self, point: Vec3) -> float:
        """Total displacement at a point, in millimetres."""
        total = 0.0
        px, py, pz = point
        for (lx, ly, lz), radius, amplitude, mirrored in self.landmarks:
            for sx in ((lx, -lx) if mirrored and abs(lx) > 1e-6 else (lx,)):
                dx = px - sx
                dy = py - ly
                dz = pz - lz
                distance = math.sqrt(dx * dx + dy * dy + dz * dz)
                if distance < radius:
                    total += amplitude * _falloff(distance, radius)
        return total


def apply_anatomy(
    mesh: Mesh,
    *,
    height: float,
    shoulder_x: float,
    hip_x: float,
    masculine: bool,
    strength: float = 1.0,
) -> Mesh:
    """Displace vertices along their normals by the anatomy field."""
    if not mesh.normals:
        mesh.recompute_normals()

    field = AnatomyField(height, shoulder_x, hip_x, masculine=masculine)
    moved: list[Vec3] = []

    for vertex, normal in zip(mesh.vertices, mesh.normals, strict=True):
        offset = field.sample(vertex) * strength
        moved.append(
            (
                vertex[0] + normal[0] * offset,
                vertex[1] + normal[1] * offset,
                vertex[2] + normal[2] * offset,
            )
        )

    mesh.vertices = moved
    mesh.recompute_normals()
    return mesh


def apply_microdetail(
    mesh: Mesh,
    *,
    scale: float,
    amplitude: float,
    octaves: int = 3,
    seed: int = 11,
) -> Mesh:
    """Add fine fractal displacement - skin texture at the millimetre scale.

    ``scale`` is the noise frequency in cycles per millimetre; ``amplitude`` is
    the displacement in millimetres. Keep amplitude well under the triangle
    edge length or the surface will look like sandpaper rather than skin.
    """
    if not mesh.normals:
        mesh.recompute_normals()

    moved: list[Vec3] = []
    for vertex, normal in zip(mesh.vertices, mesh.normals, strict=True):
        n = _fbm(
            (vertex[0] * scale, vertex[1] * scale, vertex[2] * scale),
            octaves=octaves,
            seed=seed,
        )
        offset = n * amplitude
        moved.append(
            (
                vertex[0] + normal[0] * offset,
                vertex[1] + normal[1] * offset,
                vertex[2] + normal[2] * offset,
            )
        )

    mesh.vertices = moved
    mesh.recompute_normals()
    return mesh
