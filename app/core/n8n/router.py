from typing import Optional

from fastapi import APIRouter, Query

from app.core.n8n.schemas import (
    ExecutionListResponse,
    ExecutionResponse,
    PipelineStatsResponse,
    WorkflowListResponse,
    WorkflowNodeResponse,
    WorkflowResponse,
)
from app.core.n8n.service import get_executions, get_stats, get_workflows

router = APIRouter()


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows():
    workflows, error = await get_workflows()
    items = [
        WorkflowResponse(
            id=w.id,
            name=w.name,
            active=w.active,
            created_at=w.created_at,
            updated_at=w.updated_at,
            tags=[t.get("name", "") for t in w.tags if isinstance(t, dict)],
            nodes=[
                WorkflowNodeResponse(name=n.name, type=n.type) for n in w.nodes
            ],
            node_count=len(w.nodes),
        )
        for w in workflows
    ]
    return WorkflowListResponse(data=items, total=len(items), error=error)


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    workflow_id: Optional[str] = Query(default=None, alias="workflowId"),
):
    # Build a workflow name lookup
    workflows, _ = await get_workflows()
    name_map = {w.id: w.name for w in workflows}

    executions, error = await get_executions(
        limit=limit, status=status, workflow_id=workflow_id
    )
    items = []
    for ex in executions:
        duration_ms = None
        if ex.started_at and ex.finished_at:
            delta = ex.finished_at - ex.started_at
            duration_ms = int(delta.total_seconds() * 1000)
        items.append(
            ExecutionResponse(
                id=ex.id,
                workflow_id=ex.workflow_id,
                workflow_name=name_map.get(ex.workflow_id or "", ex.workflow_name),
                status=ex.status,
                mode=ex.mode,
                started_at=ex.started_at,
                finished_at=ex.finished_at,
                duration_ms=duration_ms,
            )
        )
    return ExecutionListResponse(data=items, total=len(items), error=error)


@router.get("/stats", response_model=PipelineStatsResponse)
async def pipeline_stats():
    stats = await get_stats()
    return PipelineStatsResponse(**stats)
