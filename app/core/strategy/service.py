from app.core.strategy.models import Strategy


def recommend_strategy(user_id: str):
    return {"user_id": user_id, "strategy": "macro_rotation_v1"}


def save_strategy(strategy: Strategy):
    return strategy
