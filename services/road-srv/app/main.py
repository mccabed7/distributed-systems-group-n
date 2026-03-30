import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from redis import Redis
from redis.exceptions import RedisError


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "1"))

redis_client: Redis | None = None


def redis_key(country_code: str, booking_date: date) -> str:
    return f"road_counts:{country_code.upper()}:{booking_date.isoformat()}"


def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client


class RoadRequest(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3, description="ISO-like country code")
    booking_date: date
    road_ids: List[int] = Field(..., min_length=1)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isalpha():
            raise ValueError("country_code must contain only letters")
        return value

    @field_validator("road_ids")
    @classmethod
    def validate_road_ids(cls, value: List[int]) -> List[int]:
        if not value:
            raise ValueError("road_ids must contain at least one road id")
        for road_id in value:
            if road_id < 0:
                raise ValueError("road_ids must be non-negative integers")
        return value


class CountsResponse(BaseModel):
    country_code: str
    booking_date: date
    counts: Dict[int, int]


class HealthResponse(BaseModel):
    status: str


DECREMENT_LUA = """
local key = KEYS[1]
for i = 1, #ARGV do
    local field = ARGV[i]
    local current = tonumber(redis.call('HGET', key, field) or '0')
    if current > 0 then
        redis.call('HINCRBY', key, field, -1)
    end
end
return 1
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )
    try:
        redis_client.ping()
    except RedisError as exc:
        raise RuntimeError(f"Could not connect to Redis: {exc}") from exc
    yield
    if redis_client is not None:
        redis_client.close()


app = FastAPI(
    title="road-service",
    version="1.0.0",
    description="Service for incrementing, decrementing, and reading road booking counts per country and date.",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        get_redis().ping()
        return HealthResponse(status="ok")
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc


@app.post("/roads/increment", response_model=CountsResponse)
def increment_counts(request: RoadRequest) -> CountsResponse:
    key = redis_key(request.country_code, request.booking_date)
    client = get_redis()

    try:
        pipe = client.pipeline()
        for road_id in request.road_ids:
            pipe.hincrby(key, str(road_id), 1)
        pipe.execute()

        values = client.hmget(key, [str(road_id) for road_id in request.road_ids])
    except RedisError as exc:
        raise HTTPException(status_code=500, detail=f"Redis error: {exc}") from exc

    counts = {
        road_id: int(value) if value is not None else 0
        for road_id, value in zip(request.road_ids, values)
    }

    return CountsResponse(
        country_code=request.country_code,
        booking_date=request.booking_date,
        counts=counts,
    )


@app.post("/roads/decrement", response_model=CountsResponse)
def decrement_counts(request: RoadRequest) -> CountsResponse:
    key = redis_key(request.country_code, request.booking_date)
    client = get_redis()

    try:
        client.eval(DECREMENT_LUA, 1, key, *[str(road_id) for road_id in request.road_ids])
        values = client.hmget(key, [str(road_id) for road_id in request.road_ids])
    except RedisError as exc:
        raise HTTPException(status_code=500, detail=f"Redis error: {exc}") from exc

    counts = {
        road_id: int(value) if value is not None else 0
        for road_id, value in zip(request.road_ids, values)
    }

    return CountsResponse(
        country_code=request.country_code,
        booking_date=request.booking_date,
        counts=counts,
    )


@app.post("/roads/counts", response_model=CountsResponse)
def get_counts(request: RoadRequest) -> CountsResponse:
    key = redis_key(request.country_code, request.booking_date)
    client = get_redis()

    try:
        values = client.hmget(key, [str(road_id) for road_id in request.road_ids])
    except RedisError as exc:
        raise HTTPException(status_code=500, detail=f"Redis error: {exc}") from exc

    counts = {
        road_id: int(value) if value is not None else 0
        for road_id, value in zip(request.road_ids, values)
    }

    return CountsResponse(
        country_code=request.country_code,
        booking_date=request.booking_date,
        counts=counts,
    )