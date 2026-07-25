"""Generate the AERA hologram meshes.

    python -m tools.meshgen --out assets/hologram
    python -m tools.meshgen --detail 0.25          # finer triangles
    python -m tools.meshgen --only orb

Detail is an approximate triangle edge length in millimetres. Sub-millimetre
values are honoured up to a practical cap; see --help for why 0.01 mm is not
one of them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .character import (
    FEMININE,
    MASCULINE,
    build_character,
    character_materials,
)
from .obj import Mesh, write_mtl
from .orb import build_orb, orb_materials, subdivisions_for

#: Below this, an OBJ stops being loadable in real tools. See the note in --help.
MIN_EDGE_MM = 0.05


def _report(mesh: Mesh, path: Path) -> dict:
    size = path.stat().st_size
    dims = mesh.dimensions()
    return {
        "file": path.name,
        "vertices": len(mesh.vertices),
        "triangles": mesh.triangle_count,
        "size_mb": round(size / 1_048_576, 2),
        "dimensions_mm": tuple(round(d, 1) for d in dims),
    }


def _print_row(info: dict) -> None:
    dims = "x".join(str(d) for d in info["dimensions_mm"])
    print(
        f"  {info['file']:<24} {info['vertices']:>9,} verts  "
        f"{info['triangles']:>9,} tris  {info['size_mb']:>7.2f} MB  {dims} mm"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.meshgen",
        description="Generate the AERA voice orb and anime character meshes.",
        epilog=(
            "Note on detail: a 0.01 mm sampling of a 1.6 m figure implies ~16 billion "
            "vertices and a ~1.7 TB OBJ, which no renderer or DCC tool can open. "
            f"Edge length is therefore clamped to {MIN_EDGE_MM} mm. Fine surface detail "
            "belongs in the 4K normal maps the generated MTL files reference."
        ),
    )
    parser.add_argument("--out", default="assets/hologram", help="output directory")
    parser.add_argument(
        "--detail",
        type=float,
        default=0.5,
        help=f"approximate triangle edge length in mm (min {MIN_EDGE_MM})",
    )
    parser.add_argument(
        "--only",
        choices=["orb", "girl", "boy", "all"],
        default="all",
        help="generate a single asset",
    )
    parser.add_argument("--segments", type=int, default=48, help="radial segments for characters")
    parser.add_argument("--seed", type=int, default=7, help="orb displacement seed")
    args = parser.parse_args(argv)

    edge = args.detail
    if edge < MIN_EDGE_MM:
        print(
            f"warning: --detail {edge} mm is below the {MIN_EDGE_MM} mm floor; clamping.\n"
            f"         At 0.01 mm a 1.6 m figure needs ~16 billion vertices (~1.7 TB).\n"
            f"         Use the 4K normal maps for detail at that scale.",
            file=sys.stderr,
        )
        edge = MIN_EDGE_MM

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "textures").mkdir(exist_ok=True)

    results: list[dict] = []
    want = args.only

    # ---------------------------------------------------------------- orb
    if want in ("orb", "all"):
        level = subdivisions_for(60.0, edge)
        orb = build_orb(diameter_mm=60.0, edge_mm=edge, seed=args.seed)
        path = orb.save(out / "voice_orb.obj", mtllib="voice_orb.mtl")
        write_mtl(out / "voice_orb.mtl", orb_materials())
        info = _report(orb, path)
        info["subdivisions"] = level
        results.append(info)

    # -------------------------------------------------------------- girl
    if want in ("girl", "all"):
        girl = build_character(FEMININE, name="AERA_AnimeGirl", segments=args.segments)
        path = girl.save(out / "anime_girl.obj", mtllib="anime_girl.mtl")
        write_mtl(
            out / "anime_girl.mtl",
            character_materials(hair=(0.22, 0.55, 0.92), accent=(0.30, 0.65, 1.0), prefix="girl"),
        )
        results.append(_report(girl, path))

    # --------------------------------------------------------------- boy
    if want in ("boy", "all"):
        boy = build_character(MASCULINE, name="AERA_AnimeBoy", segments=args.segments)
        path = boy.save(out / "anime_boy.obj", mtllib="anime_boy.mtl")
        write_mtl(
            out / "anime_boy.mtl",
            character_materials(hair=(0.16, 0.14, 0.22), accent=(0.49, 0.36, 1.0), prefix="boy"),
        )
        results.append(_report(boy, path))

    print(f"\nGenerated in {out}/  (edge target {edge} mm)\n")
    for info in results:
        _print_row(info)

    total_tris = sum(r["triangles"] for r in results)
    total_mb = sum(r["size_mb"] for r in results)
    print(f"\n  total: {total_tris:,} triangles, {total_mb:.2f} MB")
    print(
        "\n  Textures: MTL files reference 4K maps in textures/. Bake or paint them\n"
        "  in your DCC tool of choice; the UVs are laid out and ready.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
