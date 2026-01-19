from datetime import datetime

from pydantic import BaseModel


class RiskProfile(BaseModel):
    risk_tolerance: str
    max_drawdown_tolerance: float
    loss_aversion_score: float


class UserPreferences(BaseModel):
    explainable_only: bool
    notification_priority: str
    reporting_frequency: str


class UserData(BaseModel):
    user_id: str
    name: str
    wealth_tier: str
    residence_country: str
    risk_profile: RiskProfile
    preferences: UserPreferences
    created_at: datetime
