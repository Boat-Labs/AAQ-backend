from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mock_workflows():
    from app.core.n8n.models import N8nWorkflow, N8nWorkflowNode

    return [
        N8nWorkflow(
            id="abc123",
            name="Caixin RSShub",
            active=True,
            nodes=[
                N8nWorkflowNode(name="RSS Feed", type="n8n-nodes-base.rssFeedRead"),
                N8nWorkflowNode(name="Postgres", type="n8n-nodes-base.postgres"),
            ],
            tags=[{"name": "news"}, {"name": "rss"}],
        ),
        N8nWorkflow(
            id="def456",
            name="Reuters RSShub",
            active=False,
            nodes=[
                N8nWorkflowNode(name="RSS Feed", type="n8n-nodes-base.rssFeedRead"),
            ],
            tags=[],
        ),
    ]


def _mock_executions():
    from app.core.n8n.models import N8nExecution

    return [
        N8nExecution(
            id="1001",
            workflowId="abc123",
            status="success",
            mode="trigger",
            startedAt="2026-02-10T08:00:00Z",
            stoppedAt="2026-02-10T08:00:05Z",
        ),
        N8nExecution(
            id="1002",
            workflowId="def456",
            status="error",
            mode="manual",
            startedAt="2026-02-10T07:00:00Z",
            stoppedAt="2026-02-10T07:00:03Z",
        ),
    ]


@patch("app.core.n8n.router.get_workflows", new_callable=AsyncMock)
def test_list_workflows(mock_get):
    mock_get.return_value = (_mock_workflows(), None)
    response = client.get("/api/n8n/workflows")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["error"] is None
    # Response uses "data" key (not "workflows")
    assert len(body["data"]) == 2
    wf = body["data"][0]
    assert wf["name"] == "Caixin RSShub"
    assert wf["active"] is True
    # camelCase aliases
    assert wf["nodeCount"] == 2
    assert wf["tags"] == ["news", "rss"]
    assert "createdAt" in wf
    assert "updatedAt" in wf


@patch("app.core.n8n.router.get_workflows", new_callable=AsyncMock)
def test_list_workflows_empty_on_error(mock_get):
    mock_get.return_value = ([], "n8n connection failed: Connection refused")
    response = client.get("/api/n8n/workflows")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["error"] is not None
    assert "connection failed" in body["error"]
    assert body["data"] == []


@patch("app.core.n8n.router.get_workflows", new_callable=AsyncMock)
@patch("app.core.n8n.router.get_executions", new_callable=AsyncMock)
def test_list_executions(mock_exec, mock_wf):
    mock_wf.return_value = (_mock_workflows(), None)
    mock_exec.return_value = (_mock_executions(), None)
    response = client.get("/api/n8n/executions?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    # Response uses "data" key (not "executions")
    ex = body["data"][0]
    # camelCase aliases
    assert ex["workflowName"] == "Caixin RSShub"
    assert ex["workflowId"] == "abc123"
    assert ex["status"] == "success"
    assert ex["mode"] == "trigger"
    assert ex["durationMs"] == 5000
    assert "startedAt" in ex
    assert "stoppedAt" in ex
    assert body["data"][1]["durationMs"] == 3000


def test_execution_numeric_id_coercion():
    """n8n API returns numeric IDs; our model should coerce to string."""
    from app.core.n8n.models import N8nExecution

    ex = N8nExecution.model_validate(
        {
            "id": 1000,
            "workflowId": 42,
            "status": "success",
            "startedAt": "2026-02-10T08:00:00Z",
        }
    )
    assert ex.id == "1000"
    assert ex.workflow_id == "42"


@patch("app.core.n8n.router.get_stats", new_callable=AsyncMock)
def test_pipeline_stats(mock_stats):
    mock_stats.return_value = {
        "total_workflows": 33,
        "active_workflows": 7,
        "total_executions": 50,
        "recent_executions_24h": 12,
        "success_rate": 95.0,
        "node_type_counts": {"n8n-nodes-base.postgres": 10},
        "error": None,
    }
    response = client.get("/api/n8n/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_workflows"] == 33
    assert body["active_workflows"] == 7
    # Frontend expects executions_24h alias
    assert body["executions_24h"] == 12
    assert body["success_rate"] == 95.0
    assert body["data_points"] == 0
    assert body["error"] is None
