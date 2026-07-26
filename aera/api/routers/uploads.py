# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""User file upload endpoints.

Anything the user drops on the dashboard or picks from a file dialog lands
here. Files are stored first and analysed second, so an agent is handed a real
path rather than a filename it cannot open.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from ...agents.base import Task
from ...core.errors import ValidationError
from ...services.uploads import CHUNK, MAX_UPLOAD_BYTES, agent_for
from ..deps import get_kernel_dep
from ..schemas import ok

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _store(kernel):
    store = getattr(kernel, "uploads", None)
    if store is None:
        raise ValidationError("the upload store is unavailable")
    return store


def _describe_size(size_bytes: int) -> str:
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} kB"
    return f"{size_bytes} bytes"


@router.get("")
async def list_uploads(kind: str | None = None, kernel=Depends(get_kernel_dep)):
    """Everything the user has uploaded, newest first."""
    store = _store(kernel)
    uploads = store.all()
    if kind:
        uploads = [u for u in uploads if u.kind == kind]
    return ok(
        {
            "uploads": [u.to_dict() for u in uploads],
            "count": len(uploads),
            "stats": store.stats(),
        }
    )


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    kernel=Depends(get_kernel_dep),
):
    """Store a file.

    Streamed to disk in chunks and hashed on the way through, so a large file
    never lands in memory whole and re-uploading the same bytes is recognised
    rather than duplicated.
    """
    store = _store(kernel)
    temp, name = store.begin(file.filename or "upload")

    digest = hashlib.sha256()
    written = 0
    try:
        with temp.open("wb") as handle:
            while chunk := await file.read(CHUNK):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    handle.close()
                    temp.unlink(missing_ok=True)
                    raise ValidationError(
                        f"{name} exceeds the {_describe_size(MAX_UPLOAD_BYTES)} upload limit"
                    )
                digest.update(chunk)
                handle.write(chunk)
    except ValidationError:
        raise
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise ValidationError(f"could not store {name}: {exc}") from exc

    if written == 0:
        temp.unlink(missing_ok=True)
        raise ValidationError(f"{name} is empty")

    record = store.commit(temp, name, digest.hexdigest(), written)
    return ok(record.to_dict(), f"Stored {record.name}")


@router.get("/routing")
async def routing_table():
    """Which agent handles which file type.

    The dashboard shows this on the drop indicator before a file is released,
    so the answer has to come from the same place the backend uses.
    """
    from ...services.uploads import AGENT_BY_KIND, KIND_BY_EXTENSION

    return ok(
        {
            "by_extension": {ext.lstrip("."): kind for ext, kind in KIND_BY_EXTENSION.items()},
            "by_kind": AGENT_BY_KIND,
            "max_upload_mb": MAX_UPLOAD_BYTES // 1_048_576,
        }
    )


@router.post("/{upload_id}/analyse")
async def analyse_upload(
    upload_id: str,
    prompt: str | None = Query(None),
    agent: str | None = Query(None),
    kernel=Depends(get_kernel_dep),
):
    """Hand a stored file to an agent.

    The agent is chosen from the file type unless one is named. Capability
    gaps surface as the agent's own refusal rather than being hidden here.
    """
    store = _store(kernel)
    record = store.get(upload_id)

    if kernel.registry is None:
        raise ValidationError("the agent registry is unavailable")

    chosen = agent or agent_for(record.name)

    task = Task(
        input=prompt or f"Analyse {record.name}",
        context={"path": str(record.path), "upload_id": record.id},
        requester="upload",
    )

    result = await kernel.registry.dispatch(task, agent_name=chosen)
    payload = result.to_public()
    payload["upload"] = record.to_dict()
    payload["agent"] = chosen
    return ok(payload, "Analysis complete" if result.success else "Analysis failed")


@router.get("/{upload_id}")
async def get_upload(upload_id: str, kernel=Depends(get_kernel_dep)):
    return ok(_store(kernel).get(upload_id).to_dict())


@router.get("/{upload_id}/file")
async def download_upload(upload_id: str, kernel=Depends(get_kernel_dep)):
    """Serve the stored bytes back."""
    record = _store(kernel).get(upload_id)
    return FileResponse(record.path, filename=record.name)


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str, kernel=Depends(get_kernel_dep)):
    _store(kernel).remove(upload_id)
    return ok({"id": upload_id}, "Deleted")
