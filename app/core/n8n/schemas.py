from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowNodeResponse(BaseModel):
    name: str
    type: str


class WorkflowResponse(BaseModel):
    model_config = {"populate_by_name": True}

    id: str
    name: str
    active: bool
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    tags: List[str] = []
    nodes: List[WorkflowNodeResponse] = []
    node_count: int = Field(default=0, alias="nodeCount")


class WorkflowListResponse(BaseModel):
    data: List[WorkflowResponse]
    total: int
    error: Optional[str] = None


class ExecutionResponse(BaseModel):
    model_config = {"populate_by_name": True}

    id: str
    workflow_id: Optional[str] = Field(default=None, alias="workflowId")
    workflow_name: Optional[str] = Field(default=None, alias="workflowName")
    status: str
    mode: Optional[str] = None
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    finished_at: Optional[datetime] = Field(default=None, alias="stoppedAt")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")


class ExecutionListResponse(BaseModel):
    data: List[ExecutionResponse]
    total: int
    error: Optional[str] = None


class PipelineStatsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    total_workflows: int = 0
    active_workflows: int = 0
    total_executions: int = 0
    executions_24h: int = Field(default=0, alias="executions_24h")
    success_rate: Optional[float] = None
    node_type_counts: Dict[str, int] = {}
    data_points: int = 0
    error: Optional[str] = None
