"""Avatar model endpoints.

Lets the user list, upload, inspect and activate their own 3D models for the
hologram. AERA ships no character of its own.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile

from ...core.errors import ValidationError
from ...hologram.loader import RECOGNISED, AvatarKind
from ..deps import get_kernel_dep
from ..schemas import ok

router = APIRouter(prefix="/avatars", tags=["hologram"])

#: Refuse anything larger outright rather than filling the disk.
MAX_UPLOAD_BYTES = 512 * 1024 * 1024
#: Read uploads in chunks so a large model never lands in memory whole.
CHUNK = 1024 * 1024


def _library(kernel):
    if kernel.avatars is None:
        raise ValidationError("the avatar library is unavailable")
    return kernel.avatars


@router.get("")
async def list_avatars(
    kind: str | None = None,
    kernel=Depends(get_kernel_dep),
):
    """Every discovered model, with its geometry summary and warnings."""
    library = _library(kernel)
    models = library.by_kind(kind) if kind else library.all()
    return ok(
        {
            "avatars": [m.to_dict() for m in models],
            "count": len(models),
            "summary": library.summary(),
        }
    )


@router.post("/scan")
async def scan_avatars(kernel=Depends(get_kernel_dep)):
    """Re-scan the avatars directory, picking up newly added files."""
    library = _library(kernel)
    models = library.scan()
    return ok(
        {"avatars": [m.to_dict() for m in models], "count": len(models)},
        f"Found {len(models)} model(s)",
    )


@router.get("/formats")
async def supported_formats():
    """What the loader accepts, and what it can actually parse."""
    from ...hologram.loader import FBX_NOTE, PARSEABLE

    return ok(
        {
            "recognised": sorted(f.lstrip(".") for f in RECOGNISED),
            "parsed": sorted(f.lstrip(".") for f in PARSEABLE),
            "recommended": "glb",
            "notes": {
                "glb": "Preferred: geometry, materials, textures and rigging in one file.",
                "gltf": "Supported; keep the .bin and textures alongside it.",
                "obj": "Supported; place the .mtl and texture files in the same folder.",
                "fbx": FBX_NOTE,
                "vrm": "Catalogued but not parsed; VRM is glTF-based, so export GLB instead.",
            },
            "max_upload_mb": MAX_UPLOAD_BYTES // 1_048_576,
        }
    )


@router.post("/upload")
async def upload_avatar(
    file: UploadFile = File(...),
    kernel=Depends(get_kernel_dep),
):
    """Upload a model into the avatars directory.

    Streams to disk in chunks and validates the extension before writing, so a
    wrong file type is rejected without consuming space.
    """
    library = _library(kernel)

    name = Path(file.filename or "model").name
    suffix = Path(name).suffix.lower()
    if suffix not in RECOGNISED and suffix not in (".mtl", ".bin", ".png", ".jpg", ".jpeg"):
        raise ValidationError(
            f"unsupported file type '{suffix}'",
            details={"accepted": sorted(f.lstrip('.') for f in RECOGNISED)},
        )

    target = library.root / name
    target.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        with target.open("wb") as handle:
            while chunk := await file.read(CHUNK):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    handle.close()
                    target.unlink(missing_ok=True)
                    raise ValidationError(
                        f"upload exceeds the {MAX_UPLOAD_BYTES // 1_048_576} MB limit"
                    )
                handle.write(chunk)
    except ValidationError:
        raise
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise ValidationError(f"could not write {name}: {exc}") from exc

    library.scan()

    # Report on the uploaded model specifically, so the caller sees its warnings.
    uploaded = next((m for m in library.all() if m.path == target), None)
    return ok(
        {
            "file": name,
            "size_mb": round(written / 1_048_576, 2),
            "model": uploaded.to_dict() if uploaded else None,
        },
        f"Uploaded {name}",
    )


@router.get("/active")
async def get_active(kernel=Depends(get_kernel_dep)):
    library = _library(kernel)
    active = library.active
    return ok({"active": active.to_dict() if active else None})


@router.post("/active")
async def set_active(
    model_id: str = Query(...),
    kernel=Depends(get_kernel_dep),
):
    """Choose which model the hologram renders."""
    library = _library(kernel)
    model = library.set_active(model_id)
    await kernel.bus.publish(
        "avatar.model.changed",
        {"id": model.id, "name": model.name, "kind": model.kind.value},
        source="hologram",
    )
    return ok(model.to_dict(), f"Active avatar: {model.name}")


@router.get("/{model_id}")
async def get_avatar(model_id: str, kernel=Depends(get_kernel_dep)):
    return ok(_library(kernel).get(model_id).to_dict())


@router.delete("/{model_id}")
async def delete_avatar(model_id: str, kernel=Depends(get_kernel_dep)):
    """Remove a model file from the library."""
    library = _library(kernel)
    model = library.get(model_id)

    # Refuse to delete outside the library root, however the id was formed.
    resolved = model.path.resolve()
    if not str(resolved).startswith(str(library.root.resolve())):
        raise ValidationError("refusing to delete a file outside the avatars directory")

    resolved.unlink(missing_ok=True)
    library.scan()
    return ok({"id": model_id}, f"Removed {model.name}")


@router.get("/{model_id}/file")
async def download_avatar(model_id: str, kernel=Depends(get_kernel_dep)):
    """Serve the raw model file, for a client-side 3D renderer."""
    from fastapi.responses import FileResponse

    model = _library(kernel).get(model_id)
    if not model.path.is_file():
        raise ValidationError(f"model file is missing: {model.path.name}")
    return FileResponse(
        model.path,
        media_type="model/gltf-binary" if model.format == "glb" else "application/octet-stream",
        filename=model.path.name,
    )


__all__ = ["router", "AvatarKind"]
