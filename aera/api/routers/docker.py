# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Docker Engine endpoints (docs/27-DOCKER.md).

Reads are open; state changes are refused unless Docker control is enabled in
configuration, which mirrors how the terminal agent is gated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...services.docker import DockerUnavailable
from ..deps import get_kernel_dep
from ..schemas import ok

router = APIRouter(prefix="/docker", tags=["docker"])


def _docker(kernel):
    client = getattr(kernel, "docker", None)
    if client is None:
        raise DockerUnavailable("the Docker connector is not configured")
    return client


@router.get("/status")
async def docker_status(kernel=Depends(get_kernel_dep)):
    """Whether Docker is reachable, and why not when it is not.

    Never raises: the UI calls this first to decide what to render, so an
    unavailable daemon is a normal result rather than an error.
    """
    return ok(_docker(kernel).status())


@router.get("/info")
async def docker_info(kernel=Depends(get_kernel_dep)):
    client = _docker(kernel)
    return ok({"version": await client.version(), "info": await client.info()})


@router.get("/containers")
async def list_containers(
    all_containers: bool = Query(True, alias="all"),
    kernel=Depends(get_kernel_dep),
):
    containers = await _docker(kernel).containers(all_containers=all_containers)
    return ok({"containers": containers, "count": len(containers)})


@router.get("/images")
async def list_images(kernel=Depends(get_kernel_dep)):
    images = await _docker(kernel).images()
    return ok({"images": images, "count": len(images)})


@router.get("/volumes")
async def list_volumes(kernel=Depends(get_kernel_dep)):
    volumes = await _docker(kernel).volumes()
    return ok({"volumes": volumes, "count": len(volumes)})


@router.get("/networks")
async def list_networks(kernel=Depends(get_kernel_dep)):
    networks = await _docker(kernel).networks()
    return ok({"networks": networks, "count": len(networks)})


@router.get("/containers/{container}/logs")
async def container_logs(
    container: str,
    tail: int = Query(200, ge=1, le=5000),
    kernel=Depends(get_kernel_dep),
):
    return ok({"container": container, "logs": await _docker(kernel).logs(container, tail=tail)})


@router.get("/containers/{container}/stats")
async def container_stats(container: str, kernel=Depends(get_kernel_dep)):
    return ok({"container": container, "stats": await _docker(kernel).stats(container)})


# --------------------------------------------------------------------------- #
# state changes -- refused unless security.allow_docker_control is on
# --------------------------------------------------------------------------- #
@router.post("/containers/{container}/start")
async def start_container(container: str, kernel=Depends(get_kernel_dep)):
    return ok(await _docker(kernel).start(container), "Container started")


@router.post("/containers/{container}/stop")
async def stop_container(container: str, kernel=Depends(get_kernel_dep)):
    return ok(await _docker(kernel).stop(container), "Container stopped")


@router.post("/containers/{container}/restart")
async def restart_container(container: str, kernel=Depends(get_kernel_dep)):
    return ok(await _docker(kernel).restart(container), "Container restarted")


@router.delete("/containers/{container}")
async def remove_container(
    container: str,
    force: bool = False,
    kernel=Depends(get_kernel_dep),
):
    return ok(await _docker(kernel).remove(container, force=force), "Container removed")
