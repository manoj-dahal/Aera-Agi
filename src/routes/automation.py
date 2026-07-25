"""Automation routes (docs/20-AUTOMATION.md — API Request trigger type)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.automation.models import ExecutionResult, TriggerType, Workflow, WorkflowCreate
from src.automation.templates import TEMPLATES

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/workflows", response_model=list[Workflow])
async def list_workflows(request: Request) -> list[Workflow]:
    return list(request.app.state.system.automation.workflows.values())


@router.post("/workflows", response_model=Workflow, status_code=201)
async def create_workflow(spec: WorkflowCreate, request: Request) -> Workflow:
    return request.app.state.system.automation.register(spec)


@router.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: int, request: Request) -> Workflow:
    workflow = request.app.state.system.automation.workflows.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return workflow


@router.delete("/workflows/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: int, request: Request) -> None:
    try:
        request.app.state.system.automation.unregister(workflow_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="workflow not found") from None


@router.post("/workflows/{workflow_id}/run", response_model=ExecutionResult)
async def run_workflow(
    workflow_id: int, request: Request, variables: dict | None = None
) -> ExecutionResult:
    """Manual Start / API Request trigger (docs/20 trigger types)."""
    try:
        return await request.app.state.system.automation.execute(
            workflow_id, TriggerType.API_REQUEST, variables
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="workflow not found") from None


@router.get("/history", response_model=list[ExecutionResult])
async def execution_history(request: Request, limit: int = 20) -> list[ExecutionResult]:
    return request.app.state.system.automation.history[-min(limit, 100):]


@router.get("/templates")
async def list_templates() -> dict[str, dict]:
    """Built-in workflow templates (docs/20)."""
    return {key: spec.model_dump() for key, spec in TEMPLATES.items()}


@router.post("/templates/{key}/install", response_model=Workflow, status_code=201)
async def install_template(key: str, request: Request) -> Workflow:
    if key not in TEMPLATES:
        raise HTTPException(status_code=404, detail="template not found")
    return request.app.state.system.automation.register(TEMPLATES[key])
