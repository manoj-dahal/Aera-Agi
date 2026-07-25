"""Automation / workflow endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...automation.engine import Action, Trigger, Workflow
from ...core.errors import ValidationError
from ..deps import get_automation
from ..schemas import WorkflowCreateRequest, WorkflowRunRequest, ok

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("")
@router.get("/workflows")
async def list_workflows(engine=Depends(get_automation)):
    return ok({"workflows": engine.list(), "count": len(engine.workflows)})


@router.post("/create")
async def create_workflow(payload: WorkflowCreateRequest, engine=Depends(get_automation)):
    try:
        workflow = Workflow(
            name=payload.name,
            description=payload.description,
            enabled=payload.enabled,
            actions=[Action(**a) for a in payload.actions],
            triggers=[Trigger(**t) for t in payload.triggers] or [Trigger()],
            variables=payload.variables,
        )
    except Exception as exc:  # noqa: BLE001 - surface schema problems as 400s
        raise ValidationError(f"invalid workflow definition: {exc}") from exc

    engine.register(workflow)
    return ok(
        {"id": workflow.id, "name": workflow.name, "actions": len(workflow.actions)},
        "Workflow created",
    )


@router.post("/run")
async def run_workflow(
    workflow_id: str = Query(...),
    payload: WorkflowRunRequest | None = None,
    engine=Depends(get_automation),
):
    run = await engine.run(workflow_id, variables=(payload.variables if payload else None))
    return ok(run.to_public(), f"Workflow finished with status {run.status.value}")


@router.get("/jobs")
@router.get("/runs")
async def list_runs(limit: int = Query(20, ge=1, le=100), engine=Depends(get_automation)):
    return ok({"runs": engine.history(limit)})


@router.post("/stop")
async def stop_automation(workflow_id: str = Query(...), engine=Depends(get_automation)):
    workflow = engine.get(workflow_id)
    workflow.enabled = False
    return ok({"id": workflow.id, "enabled": False}, "Workflow disabled")


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, engine=Depends(get_automation)):
    engine.remove(workflow_id)
    return ok({"id": workflow_id}, "Workflow removed")
