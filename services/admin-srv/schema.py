import uuid
from pydantic import BaseModel, Field


class CreateRegistrationRequest(BaseModel):
    user_id: uuid.UUID
    registration_id: str = Field(..., min_length=1)
