from fastapi import APIRouter

from app.core.user.models import UserData
from app.core.user.schemas import CreateUserRequest
from app.core.user.service import create_user

router = APIRouter()


@router.post("/")
def create_user_endpoint(payload: CreateUserRequest):
    return {"message": "User created", "user": create_user(payload.user_id)}


@router.get("/{user_id}")
def get_user(user_id: str):
    return {"user_id": user_id}


@router.post("/data")
def create_user_data(user: UserData):
    return {"message": "User data stored", "user": user}
