from pydantic import BaseModel, EmailStr
import uuid

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class CreateResponse(BaseModel):
    id: uuid.UUID
    username: str

class LoginResponse(BaseModel):
    id: uuid.UUID
    username: str
    token: str
