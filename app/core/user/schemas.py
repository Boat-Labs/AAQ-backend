from datetime import datetime

from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    user_id: str
    name: str


class CreateUserResponse(BaseModel):
    user_id: str
    created_at: datetime
