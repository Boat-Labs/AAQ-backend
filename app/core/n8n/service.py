import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.n8n.models import N8nExecution, N8nWorkflow
from app.core.shared.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


def _headers() -> Dict[str, str]:
    return {"X-N8N-API-KEY": settings.n8n_api_key}


def _base_url() -> str:
    return settings.n8n_base_url.rstrip("/")


async def get_workflows(
    tags: Optional[str] = None,
) -> Tuple[List[N8nWorkflow], Optional[str]]:
    """Fetch workflows from n8n. Optionally filter by tag name. Returns (workflows, error_message)."""
    url = f"{_base_url()}/api/v1/workflows"
    params: Dict[str, Any] = {}
    if tags:
        params["tags"] = tags
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_workflows = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(raw_workflows, list):
                raw_workflows = []
            workflows = [N8nWorkflow.model_validate(w) for w in raw_workflows]
            return workflows, None
    except httpx.HTTPStatusError as e:
        msg = f"n8n API returned {e.response.status_code}"
        logger.warning(msg)
        return [], msg
    except Exception as e:
        msg = f"n8n connection failed: {e}"
        logger.warning(msg)
        return [], msg


async def get_executions(
    limit: int = 20,
    status: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> Tuple[List[N8nExecution], Optional[str]]:
    """Fetch recent executions from n8n. Returns (executions, error_message)."""
    url = f"{_base_url()}/api/v1/executions"
    params: Dict[str, Any] = {"limit": limit}
    if status:
        params["status"] = status
    if workflow_id:
        params["workflowId"] = workflow_id
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_executions = (
                data.get("data", data) if isinstance(data, dict) else data
            )
            if not isinstance(raw_executions, list):
                raw_executions = []
            executions = [N8nExecution.model_validate(e) for e in raw_executions]
            return executions, None
    except httpx.HTTPStatusError as e:
        msg = f"n8n API returned {e.response.status_code}"
        logger.warning(msg)
        return [], msg
    except Exception as e:
        msg = f"n8n connection failed: {e}"
        logger.warning(msg)
        return [], msg


async def get_stats(tags: Optional[str] = None) -> Dict[str, Any]:
    """Compute aggregate pipeline statistics from workflows and executions."""
    workflows, wf_err = await get_workflows(tags=tags)
    executions, ex_err = await get_executions(limit=100)

    # If filtering by tags, only count executions from matching workflows
    if tags and workflows:
        tagged_ids = {w.id for w in workflows}
        executions = [
            e for e in executions if str(e.workflow_id) in tagged_ids
        ]

    error = wf_err or ex_err

    total_workflows = len(workflows)
    active_workflows = sum(1 for w in workflows if w.active)

    # Count node types across all workflows
    node_type_counter: Counter[str] = Counter()
    for w in workflows:
        for node in w.nodes:
            node_type_counter[node.type] += 1

    # Count executions in the last 24 hours
    now = datetime.now(timezone.utc)
    recent_24h = 0
    success_count = 0
    total_with_status = 0
    for ex in executions:
        if ex.started_at:
            delta = now - ex.started_at.replace(tzinfo=timezone.utc)
            if delta.total_seconds() < 86400:
                recent_24h += 1
        if ex.status in ("success", "error"):
            total_with_status += 1
            if ex.status == "success":
                success_count += 1

    success_rate = (
        round(success_count / total_with_status * 100, 1)
        if total_with_status > 0
        else None
    )

    return {
        "total_workflows": total_workflows,
        "active_workflows": active_workflows,
        "total_executions": len(executions),
        "recent_executions_24h": recent_24h,
        "success_rate": success_rate,
        "node_type_counts": dict(node_type_counter.most_common(20)),
        "error": error,
    }
