from fastapi import APIRouter

from app.core.goal.models import Goal
from app.core.goal.service import create_goal

router = APIRouter()


@router.post("/")
def create_goal_endpoint(goal: Goal):
    return {"message": "Goal created", "goal": create_goal(goal)}
