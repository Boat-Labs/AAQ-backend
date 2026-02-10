from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class N8nWorkflowNode(BaseModel):
    """A single node within an n8n workflow."""

    name: str
    type: str
    position: Optional[List[float]] = None


class N8nWorkflow(BaseModel):
    """Represents an n8n workflow from the API."""

    id: str
    name: str
    active: bool = False
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    tags: List[Dict[str, Any]] = []
    nodes: List[N8nWorkflowNode] = []

    model_config = {"populate_by_name": True}


class N8nExecution(BaseModel):
    """Represents an n8n workflow execution."""

    id: str
    workflow_id: Optional[str] = Field(default=None, alias="workflowId")
    workflow_name: Optional[str] = None
    status: str = "unknown"
    mode: Optional[str] = None
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    finished_at: Optional[datetime] = Field(default=None, alias="stoppedAt")

    model_config = {"populate_by_name": True}

    @field_validator("id", "workflow_id", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Union[int, str, None]) -> Optional[str]:
        """n8n API may return numeric IDs; coerce to string."""
        if v is None:
            return None
        return str(v)
