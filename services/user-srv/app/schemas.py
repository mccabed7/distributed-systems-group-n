from pydantic import BaseModel, EmailStr
import uuid

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class CreateResponse(BaseModel):
    id: uuid.UUID

class LoginResponse(BaseModel):
    id: uuid.UUID
    token: str
