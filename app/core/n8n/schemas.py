from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class WorkflowNodeResponse(BaseModel):
    name: str
    type: str


class WorkflowResponse(BaseModel):
    id: str
    name: str
    active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = []
    nodes: List[WorkflowNodeResponse] = []
    node_count: int = 0


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]
    total: int
    error: Optional[str] = None


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    status: str
    mode: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ExecutionListResponse(BaseModel):
    executions: List[ExecutionResponse]
    total: int
    error: Optional[str] = None


class PipelineStatsResponse(BaseModel):
    total_workflows: int = 0
    active_workflows: int = 0
    total_executions: int = 0
    recent_executions_24h: int = 0
    success_rate: Optional[float] = None
    node_type_counts: Dict[str, int] = {}
    error: Optional[str] = None
