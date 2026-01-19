from datetime import datetime

from app.core.user.schemas import CreateUserResponse


def create_user(user_id: str) -> CreateUserResponse:
    return CreateUserResponse(user_id=user_id, created_at=datetime.utcnow())
