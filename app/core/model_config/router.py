from fastapi import APIRouter

from app.core.tradingagents.llm_clients.validators import VALID_MODELS

router = APIRouter()


@router.get("/providers")
def list_providers() -> dict[str, list[str]]:
    """Return available LLM providers and their supported models."""
    return VALID_MODELS
