from fastapi import APIRouter

from app.core.activities.models import Decision, Feedback
from app.core.activities.service import record_decision, record_feedback

router = APIRouter()


@router.post("/decision")
def create_decision(decision: Decision):
    return {"message": "Decision recorded", "decision": record_decision(decision)}


@router.post("/feedback")
def create_feedback(feedback: Feedback):
    return {"message": "Feedback recorded", "feedback": record_feedback(feedback)}
