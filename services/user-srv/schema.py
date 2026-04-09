import uuid
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    id: uuid.UUID
    username: str
    token: str


RegisterRequest = LoginRequest


class RegisterResponse(BaseModel):
    id: uuid.UUID


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
