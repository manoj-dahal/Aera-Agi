# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Stylised anime character generator.

Builds a humanoid base mesh from parametric primitives: a lathed torso, tapered
limbs, and a proportioned head with hair volume. The result is a clean,
quad-derived base mesh suitable for sculpting or rigging — not a finished
production character, which needs an artist.

Proportions follow anime convention: a head-to-height ratio near 1:6.5 rather
than the 1:7.5 of realistic anatomy, with larger cranium and eye sockets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .detail import apply_anatomy, apply_microdetail
from .obj import Material, Mesh, Vec3


@dataclass(frozen=True)
class Proportions:
    """Body measurements in millimetres, driving the whole figure."""

    height: float = 1600.0
    #: Height divided by head length; anime styling sits around 6.0-6.8.
    head_ratio: float = 6.5
    shoulder_width: float = 0.24      # fraction of height
    hip_width: float = 0.19
    waist_width: float = 0.155
    chest_depth: float = 0.105
    limb_thickness: float = 0.040
    #: Chest projection; distinguishes the feminine and masculine builds.
    bust: float = 0.0
    #: Extra deltoid and trapezius mass.
    shoulder_mass: float = 0.0
    hair_volume: float = 1.0

    @property
    def head_length(self) -> float:
        return self.height / self.head_ratio


FEMININE = Proportions(
    height=1580.0,
    head_ratio=6.6,
    shoulder_width=0.215,
    hip_width=0.205,
    waist_width=0.140,
    chest_depth=0.100,
    limb_thickness=0.036,
    bust=0.052,
    shoulder_mass=0.0,
    hair_volume=1.55,
)

MASCULINE = Proportions(
    height=1720.0,
    head_ratio=6.9,
    shoulder_width=0.258,
    hip_width=0.180,
    waist_width=0.168,
    chest_depth=0.118,
    limb_thickness=0.046,
    bust=0.010,
    shoulder_mass=0.022,
    hair_volume=0.95,
)


def _lathe(
    profile: list[tuple[float, float, float]],
    segments: int,
    *,
    name: str = "lathe",
    material: str | None = None,
    close_top: bool = True,
    close_bottom: bool = True,
) -> Mesh:
    """Revolve a profile around the Y axis.

    Each profile entry is ``(y, radius_x, radius_z)``, so cross-sections can be
    elliptical — a torso is not circular.
    """
    mesh = Mesh(name=name, material=material)
    rings: list[list[int]] = []

    for row, (y, rx, rz) in enumerate(profile):
        ring: list[int] = []
        v = row / max(1, len(profile) - 1)
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            x = math.cos(theta) * rx
            z = math.sin(theta) * rz
            ring.append(mesh.add_vertex((x, y, z), uv=(i / segments, v)))
        rings.append(ring)

    for r in range(len(rings) - 1):
        lower, upper = rings[r], rings[r + 1]
        for i in range(segments):
            j = (i + 1) % segments
            mesh.add_quad(lower[i], lower[j], upper[j], upper[i])

    # Caps: a fan to a centre vertex at each end.
    if close_bottom:
        y, _, _ = profile[0]
        centre = mesh.add_vertex((0.0, y, 0.0), uv=(0.5, 0.0))
        for i in range(segments):
            j = (i + 1) % segments
            mesh.add_triangle(centre, rings[0][j], rings[0][i])
    if close_top:
        y, _, _ = profile[-1]
        centre = mesh.add_vertex((0.0, y, 0.0), uv=(0.5, 1.0))
        for i in range(segments):
            j = (i + 1) % segments
            mesh.add_triangle(centre, rings[-1][i], rings[-1][j])

    return mesh


def _limb(
    start: Vec3,
    end: Vec3,
    r_start: float,
    r_end: float,
    segments: int,
    rows: int,
    *,
    name: str,
    material: str | None = None,
) -> Mesh:
    """A tapered capsule between two points, with a slight mid-limb bulge."""
    mesh = Mesh(name=name, material=material)

    axis = (end[0] - start[0], end[1] - start[1], end[2] - start[2])
    length = math.sqrt(sum(c * c for c in axis))
    if length < 1e-9:
        return mesh
    direction = tuple(c / length for c in axis)

    # Build an orthonormal frame around the limb axis.
    up = (0.0, 0.0, 1.0) if abs(direction[1]) > 0.99 else (0.0, 1.0, 0.0)
    right = _cross(direction, up)
    right = _norm(right)
    forward = _norm(_cross(direction, right))

    rings: list[list[int]] = []
    for row in range(rows + 1):
        t = row / rows
        # Muscle bulge: widest around a third of the way along.
        bulge = 1.0 + 0.10 * math.sin(math.pi * t) * (1.0 - abs(t - 0.35))
        radius = (r_start * (1 - t) + r_end * t) * bulge
        centre = tuple(start[i] + axis[i] * t for i in range(3))

        ring: list[int] = []
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            cos_a, sin_a = math.cos(theta), math.sin(theta)
            position = tuple(
                centre[k] + (right[k] * cos_a + forward[k] * sin_a) * radius for k in range(3)
            )
            ring.append(mesh.add_vertex(position, uv=(i / segments, t)))  # type: ignore[arg-type]
        rings.append(ring)

    for r in range(rows):
        lower, upper = rings[r], rings[r + 1]
        for i in range(segments):
            j = (i + 1) % segments
            mesh.add_quad(lower[i], lower[j], upper[j], upper[i])

    for ring, cap_y, flip in ((rings[0], start, True), (rings[-1], end, False)):
        centre = mesh.add_vertex(cap_y, uv=(0.5, 0.0 if flip else 1.0))
        for i in range(segments):
            j = (i + 1) % segments
            if flip:
                mesh.add_triangle(centre, ring[j], ring[i])
            else:
                mesh.add_triangle(centre, ring[i], ring[j])

    return mesh


def _sphere(
    centre: Vec3,
    radius: float,
    segments: int,
    *,
    name: str = "joint",
    material: str | None = None,
    squash: float = 1.0,
) -> Mesh:
    """A UV sphere, used to bridge limb sockets so joints read as continuous."""
    mesh = Mesh(name=name, material=material)
    rows = max(4, segments // 2)
    rings: list[list[int]] = []

    for r in range(rows + 1):
        phi = math.pi * r / rows
        y = math.cos(phi) * radius * squash
        ring_r = math.sin(phi) * radius
        ring: list[int] = []
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            ring.append(
                mesh.add_vertex(
                    (
                        centre[0] + math.cos(theta) * ring_r,
                        centre[1] + y,
                        centre[2] + math.sin(theta) * ring_r,
                    ),
                    uv=(i / segments, r / rows),
                )
            )
        rings.append(ring)

    for r in range(rows):
        lower, upper = rings[r], rings[r + 1]
        for i in range(segments):
            j = (i + 1) % segments
            mesh.add_quad(lower[i], lower[j], upper[j], upper[i])
    return mesh


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v: Vec3) -> Vec3:
    length = math.sqrt(sum(c * c for c in v))
    return tuple(c / length for c in v) if length else (1.0, 0.0, 0.0)  # type: ignore[return-value]


def _torso(p: Proportions, segments: int) -> Mesh:
    """Torso from hip to neck, with elliptical cross-sections."""
    h = p.height
    shoulder_y = h * 0.815
    hip_y = h * 0.505

    sw = h * p.shoulder_width / 2
    hw = h * p.hip_width / 2
    ww = h * p.waist_width / 2
    depth = h * p.chest_depth / 2
    bust = h * p.bust

    # (fraction along torso, half-width, half-depth)
    stations = [
        (0.00, hw * 0.92, depth * 0.86),                      # hips
        (0.16, hw, depth * 0.90),                             # widest hip
        (0.34, ww, depth * 0.80),                             # waist
        (0.52, ww * 1.14, depth * 0.94 + bust * 0.55),        # lower ribcage
        (0.68, sw * 0.86, depth * 1.02 + bust),               # chest
        (0.84, sw * (1.0 + p.shoulder_mass * 4), depth * 0.96),  # shoulders
        (0.94, sw * 0.52, depth * 0.66),                      # shoulder taper
        (1.00, h * 0.032, h * 0.030),                         # neck base
    ]

    profile = [
        (hip_y + (shoulder_y - hip_y) * t, rx, rz) for t, rx, rz in stations
    ]
    return _lathe(profile, segments, name="torso", material="skin", close_top=False)


def _head(p: Proportions, segments: int) -> Mesh:
    """Head, jaw and hair volume.

    Anime styling: a rounded cranium, a narrow tapered chin, and hair treated as
    a separate shell rather than modelled strands.
    """
    h = p.height
    head_len = p.head_length
    chin_y = h - head_len
    centre_y = chin_y + head_len * 0.56

    hw = head_len * 0.36  # half-width at the cheekbones
    hd = head_len * 0.40  # half-depth

    stations = [
        (0.00, hw * 0.18, hd * 0.24),  # chin point
        (0.10, hw * 0.52, hd * 0.62),  # jaw
        (0.24, hw * 0.80, hd * 0.88),  # cheek
        (0.40, hw * 0.96, hd * 1.00),  # cheekbone, widest
        (0.58, hw * 1.00, hd * 1.02),  # eye line
        (0.74, hw * 0.97, hd * 0.99),  # brow
        (0.88, hw * 0.84, hd * 0.86),  # upper cranium
        (0.97, hw * 0.50, hd * 0.52),
        (1.00, hw * 0.14, hd * 0.15),  # crown
    ]
    profile = [(chin_y + head_len * t, rx, rz) for t, rx, rz in stations]
    head = _lathe(profile, segments, name="head", material="skin")

    # Hair shell: an offset copy of the cranium, opened at the face.
    hair_scale = 1.0 + 0.085 * p.hair_volume
    hair_stations = [
        (0.42, hw * 1.02 * hair_scale, hd * 1.04 * hair_scale),
        (0.60, hw * 1.06 * hair_scale, hd * 1.08 * hair_scale),
        (0.78, hw * 0.98 * hair_scale, hd * 1.00 * hair_scale),
        (0.92, hw * 0.80 * hair_scale, hd * 0.84 * hair_scale),
        (1.02, hw * 0.30 * hair_scale, hd * 0.32 * hair_scale),
    ]
    hair_profile = [(chin_y + head_len * t, rx, rz) for t, rx, rz in hair_stations]
    hair = _lathe(hair_profile, segments, name="hair", material="hair", close_bottom=False)

    # Longer hair falls behind the shoulders on the feminine build.
    if p.hair_volume > 1.2:
        fall = _lathe(
            [
                (chin_y - head_len * 0.10, hw * 0.94, hd * 0.62),
                (chin_y - head_len * 0.80, hw * 1.02, hd * 0.58),
                (chin_y - head_len * 1.60, hw * 0.86, hd * 0.46),
                (chin_y - head_len * 2.10, hw * 0.42, hd * 0.24),
            ],
            segments,
            name="hair_fall",
            material="hair",
        )
        # Push it behind the body so it reads as hair, not a collar.
        fall.translate(0.0, 0.0, -hd * 0.34)
        hair.merge(fall)

    head.merge(hair)
    _ = centre_y
    return head


def build_character(
    p: Proportions,
    *,
    name: str,
    segments: int = 48,
    rows: int = 18,
    anatomy: float = 0.0,
    microdetail: float = 0.0,
) -> Mesh:
    """Assemble a full humanoid from the proportion set.

    ``anatomy`` scales the anatomical displacement pass (clavicle, spine,
    scapula, knee caps and so on). ``microdetail`` is the skin-scale noise
    amplitude in millimetres. Both are off by default so the base mesh stays
    clean for sculpting.
    """
    h = p.height
    figure = Mesh(name=name, material="skin")

    figure.merge(_torso(p, segments))
    figure.merge(_head(p, segments))

    # Neck bridges the torso and jaw.
    figure.merge(
        _limb(
            (0.0, h * 0.800, 0.0),
            (0.0, h * 0.862, 0.0),
            h * 0.032, h * 0.029,
            segments, 4, name="neck", material="skin",
        )
    )

    limb_r = h * p.limb_thickness / 2
    shoulder_x = h * p.shoulder_width / 2
    hip_x = h * p.hip_width / 2

    # Shoulder height: the torso is widest here, so the arm socket sits inside
    # the body silhouette rather than out at the neck taper.
    shoulder_y = h * 0.782
    elbow_y = h * 0.628
    wrist_y = h * 0.472

    for side in (-1, 1):
        socket = (side * shoulder_x * 0.80, shoulder_y, 0.0)
        elbow = (side * shoulder_x * 0.94, elbow_y, 0.0)
        wrist = (side * shoulder_x * 0.99, wrist_y, 0.0)

        # Deltoid: bridges the torso and the upper arm so the joint is solid.
        figure.merge(
            _sphere(socket, limb_r * 1.48, segments // 2,
                    name=f"deltoid_{side}", material="skin", squash=0.92)
        )
        figure.merge(
            _limb(
                socket, elbow,
                limb_r * 1.20, limb_r * 0.90,
                segments // 2, rows // 2, name=f"upper_arm_{side}", material="skin",
            )
        )
        figure.merge(
            _sphere(elbow, limb_r * 0.94, segments // 3,
                    name=f"elbow_{side}", material="skin")
        )
        figure.merge(
            _limb(
                elbow, wrist,
                limb_r * 0.90, limb_r * 0.64,
                segments // 2, rows // 2, name=f"forearm_{side}", material="skin",
            )
        )
        # Hand as a flattened block rather than modelled fingers.
        figure.merge(
            _limb(
                wrist,
                (side * shoulder_x * 1.01, h * 0.400, 0.0),
                limb_r * 0.64, limb_r * 0.40,
                segments // 3, 4, name=f"hand_{side}", material="skin",
            )
        )

        # Leg: hip socket, thigh, knee, calf.
        hip_socket = (side * hip_x * 0.56, h * 0.512, 0.0)
        knee = (side * hip_x * 0.60, h * 0.278, 0.0)
        ankle = (side * hip_x * 0.58, h * 0.038, 0.0)

        figure.merge(
            _sphere(hip_socket, limb_r * 1.80, segments // 2,
                    name=f"hip_{side}", material="skin", squash=0.88)
        )
        figure.merge(
            _limb(
                hip_socket, knee,
                limb_r * 1.72, limb_r * 1.08,
                segments // 2, rows // 2, name=f"thigh_{side}", material="skin",
            )
        )
        figure.merge(
            _sphere(knee, limb_r * 1.14, segments // 3,
                    name=f"knee_{side}", material="skin")
        )
        figure.merge(
            _limb(
                knee, ankle,
                limb_r * 1.08, limb_r * 0.58,
                segments // 2, rows // 2, name=f"calf_{side}", material="skin",
            )
        )
        # Foot extends forward along +Z from the ankle.
        figure.merge(
            _limb(
                (ankle[0], h * 0.026, -h * 0.006),
                (ankle[0], h * 0.014, h * 0.072),
                limb_r * 0.60, limb_r * 0.42,
                segments // 3, 4, name=f"foot_{side}", material="skin",
            )
        )

    figure.recompute_normals()

    # Detail passes run last: they displace along finished normals, so the
    # landmarks land on the real surface rather than an intermediate one.
    if anatomy > 0:
        apply_anatomy(
            figure,
            height=h,
            shoulder_x=shoulder_x,
            hip_x=hip_x,
            masculine=p.shoulder_mass > 0.015,
            strength=anatomy,
        )
    if microdetail > 0:
        # Frequency chosen so features span a few triangles at typical density.
        apply_microdetail(figure, scale=0.055, amplitude=microdetail, octaves=3)

    return figure


def character_materials(*, hair: Vec3, accent: Vec3, prefix: str) -> list[Material]:
    """Toon-shaded materials referencing the 4K texture set."""
    return [
        Material(
            name="skin",
            diffuse=(0.98, 0.87, 0.82),
            specular=(0.22, 0.20, 0.20),
            shininess=28.0,
            diffuse_map=f"textures/{prefix}_skin_diffuse_4k.png",
            normal_map=f"textures/{prefix}_skin_normal_4k.png",
        ),
        Material(
            name="hair",
            diffuse=hair,
            specular=(0.62, 0.62, 0.70),
            shininess=96.0,
            diffuse_map=f"textures/{prefix}_hair_diffuse_4k.png",
            normal_map=f"textures/{prefix}_hair_normal_4k.png",
        ),
        Material(
            name="accent",
            diffuse=accent,
            specular=(0.4, 0.4, 0.45),
            emissive=tuple(c * 0.25 for c in accent),  # type: ignore[arg-type]
            shininess=64.0,
        ),
    ]
