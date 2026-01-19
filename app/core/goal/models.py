from pydantic import BaseModel


class Goal(BaseModel):
    goal_id: str
    description: str
    target_amount: float
    horizon_months: int
