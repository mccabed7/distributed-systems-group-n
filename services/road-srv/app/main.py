import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Dict, List, Literal, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from redis import Redis
from redis.exceptions import RedisError


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "1"))

MAX_CAPACITY_PER_ROAD = 10

redis_client: Redis | None = None


def redis_key(booking_date: date) -> str:
    return f"road_counts:{booking_date.isoformat()}"


def road_field(country_code: str, road_id: int) -> str:
    return f"{country_code.upper()}:{road_id}"


def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client


class RoadEntry(BaseModel):
    road_id: int = Field(..., ge=0)
    country_code: str = Field(..., min_length=2, max_length=3)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isalpha():
            raise ValueError("country_code must contain only letters")
        return value


class RoadRequest(BaseModel):
    booking_date: date
    roads: List[RoadEntry] = Field(..., min_length=1)

    @field_validator("roads")
    @classmethod
    def validate_roads(cls, value: List[RoadEntry]) -> List[RoadEntry]:
        if not value:
            raise ValueError("roads must contain at least one road")
        return value


class RoadCountEntry(BaseModel):
    road_id: int
    country_code: str
    count: int


class CountsResponse(BaseModel):
    booking_date: date
    roads: List[RoadCountEntry]


class IncrementSuccessResponse(BaseModel):
    status: Literal["success"]
    booking_date: date
    roads: List[RoadCountEntry]


class IncrementFailureResponse(BaseModel):
    status: Literal["failed"]
    booking_date: date
    full_roads: List[RoadEntry]
    roads: List[RoadCountEntry]


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


INCREMENT_TRANSACTIONAL_LUA = """
local key = KEYS[1]
local max_capacity = tonumber(ARGV[1])

local full_roads = {}

for i = 2, #ARGV do
    local field = ARGV[i]
    local current = tonumber(redis.call('HGET', key, field) or '0')
    if current >= max_capacity then
        table.insert(full_roads, field)
    end
end

if #full_roads > 0 then
    local result = {'failed'}
    for i = 1, #full_roads do
        table.insert(result, full_roads[i])
    end
    return result
end

for i = 2, #ARGV do
    local field = ARGV[i]
    redis.call('HINCRBY', key, field, 1)
end

return {'success'}
"""


def fetch_counts_for_roads(client: Redis, booking_date: date, roads: List[RoadEntry]) -> List[RoadCountEntry]:
    key = redis_key(booking_date)
    fields = [road_field(road.country_code, road.road_id) for road in roads]

    values = client.hmget(key, fields)

    return [
        RoadCountEntry(
            road_id=road.road_id,
            country_code=road.country_code,
            count=int(value) if value is not None else 0,
        )
        for road, value in zip(roads, values)
    ]


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
    version="1.3.0",
    description="Service for incrementing, decrementing, and reading road booking counts per road-country and date.",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        get_redis().ping()
        return HealthResponse(status="ok")
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc


@app.post(
    "/roads/increment",
    response_model=Union[IncrementSuccessResponse, IncrementFailureResponse],
)
def increment_counts(
    request: RoadRequest,
) -> Union[IncrementSuccessResponse, IncrementFailureResponse]:
    client = get_redis()
    key = redis_key(request.booking_date)
    fields = [road_field(road.country_code, road.road_id) for road in request.roads]

    try:
        result = client.eval(
            INCREMENT_TRANSACTIONAL_LUA,
            1,
            key,
            str(MAX_CAPACITY_PER_ROAD),
            *fields,
        )

        current_counts = fetch_counts_for_roads(client, request.booking_date, request.roads)

    except RedisError as exc:
        raise HTTPException(status_code=500, detail=f"Redis error: {exc}") from exc

    if not result or result[0] not in ("success", "failed"):
        raise HTTPException(status_code=500, detail="Unexpected Redis response")

    if result[0] == "failed":
        full_fields = set(result[1:])
        full_roads = [
            RoadEntry(road_id=road.road_id, country_code=road.country_code)
            for road in request.roads
            if road_field(road.country_code, road.road_id) in full_fields
        ]

        return IncrementFailureResponse(
            status="failed",
            booking_date=request.booking_date,
            full_roads=full_roads,
            roads=current_counts,
        )

    return IncrementSuccessResponse(
        status="success",
        booking_date=request.booking_date,
        roads=current_counts,
    )


@app.post("/roads/decrement", response_model=CountsResponse)
def decrement_counts(request: RoadRequest) -> CountsResponse:
    client = get_redis()
    key = redis_key(request.booking_date)
    fields = [road_field(road.country_code, road.road_id) for road in request.roads]

    try:
        client.eval(DECREMENT_LUA, 1, key, *fields)
        current_counts = fetch_counts_for_roads(client, request.booking_date, request.roads)
    except RedisError as exc:
        raise HTTPException(status_code=500, detail=f"Redis error: {exc}") from exc

    return CountsResponse(
        booking_date=request.booking_date,
        roads=current_counts,
    )


@app.post("/roads/counts", response_model=CountsResponse)
def get_counts(request: RoadRequest) -> CountsResponse:
    client = get_redis()

    try:
        current_counts = fetch_counts_for_roads(client, request.booking_date, request.roads)
    except RedisError as exc:
        raise HTTPException(status_code=500, detail=f"Redis error: {exc}") from exc

    return CountsResponse(
        booking_date=request.booking_date,
        roads=current_counts,
    )