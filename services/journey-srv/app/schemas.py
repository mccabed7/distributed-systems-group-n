import json
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class WaySegment(BaseModel):
    way_id: int
    country: str | None  # None if Nominatim could not resolve


class CreateJourneyRequest(BaseModel):
    origin: str = Field(..., min_length=1, example="Dublin, Ireland")
    destination: str = Field(..., min_length=1, example="Cork, Ireland")


class JourneyResponse(BaseModel):
    id: str
    origin: str
    destination: str
    distance_m: float
    duration_s: float
    way_ids: list[WaySegment]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("way_ids", mode="before")
    @classmethod
    def parse_way_ids(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
