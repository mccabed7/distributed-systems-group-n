import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import date
from enum import Enum
from typing import Annotated, List, Optional

import asyncpg
import httpx
from aiokafka import AIOKafkaProducer
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://booking:booking@localhost:5432/booking"
)
REPLICA_DATABASE_URL = os.getenv("REPLICA_DATABASE_URL", DATABASE_URL)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_NOTIFICATIONS_TOPIC = os.getenv("KAFKA_NOTIFICATIONS_TOPIC", "notifications")
ROAD_SRV_URL = os.getenv("ROAD_SRV_URL", "http://road-srv:8000")
JOURNEY_SRV_URL = os.getenv("JOURNEY_SRV_URL", "")  # optional

db_pool: asyncpg.Pool | None = None
db_replica_pool: asyncpg.Pool | None = None
kafka_producer: AIOKafkaProducer | None = None
http_client: httpx.AsyncClient | None = None

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS bookings (
    id            UUID        PRIMARY KEY,
    user_id       TEXT        NOT NULL,
    status        TEXT        NOT NULL DEFAULT 'PENDING',
    start_location TEXT       NOT NULL,
    end_location  TEXT        NOT NULL,
    booking_date  DATE        NOT NULL,
    country_code  TEXT        NOT NULL,
    road_ids      INTEGER[]   NOT NULL DEFAULT '{}',
    request_id    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

MIGRATE_SQL = """
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS request_id TEXT;

ALTER TABLE bookings ALTER COLUMN road_ids TYPE BIGINT[] USING road_ids::BIGINT[];
"""


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CreateBookingRequest(BaseModel):
    start_location: str = Field(..., min_length=1)
    end_location: str = Field(..., min_length=1)
    booking_date: date
    country_code: str = Field(..., min_length=2, max_length=3)
    road_ids: Optional[List[int]] = None

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value.isalpha():
            raise ValueError("country_code must contain only letters")
        return value

    @field_validator("road_ids")
    @classmethod
    def validate_road_ids(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is not None:
            for road_id in value:
                if road_id < 0:
                    raise ValueError("road_ids must be non-negative integers")
        return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, db_replica_pool, kafka_producer, http_client

    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    async with db_pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
        await conn.execute(MIGRATE_SQL)
    logger.info("Database pool ready")

    db_replica_pool = await asyncpg.create_pool(
        REPLICA_DATABASE_URL, min_size=2, max_size=10
    )
    logger.info("Replica database pool ready")

    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    await kafka_producer.start()
    logger.info("Kafka producer ready")

    http_client = httpx.AsyncClient(timeout=10.0)

    yield

    await kafka_producer.stop()
    await http_client.aclose()
    await db_pool.close()
    await db_replica_pool.close()


app = FastAPI(title="booking-service", version="1.0.0", lifespan=lifespan)


def get_db() -> asyncpg.Pool:
    if db_pool is None:
        raise RuntimeError("DB pool not initialized")
    return db_pool


def get_replica_db() -> asyncpg.Pool:
    if db_replica_pool is None:
        raise RuntimeError("Replica DB pool not initialized")
    return db_replica_pool


def get_kafka() -> AIOKafkaProducer:
    if kafka_producer is None:
        raise RuntimeError("Kafka producer not initialized")
    return kafka_producer


def get_http() -> httpx.AsyncClient:
    if http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return http_client


async def _publish_notification(
    user_id: str, booking_id: str, status: BookingStatus
) -> None:
    event = {
        "delivery_type": "PUSH",
        "user_id": user_id,
        "message_id": str(uuid.uuid4()),
        "content": f"Your booking {booking_id} is {status.value}.",
    }
    try:
        await get_kafka().send_and_wait(
            KAFKA_NOTIFICATIONS_TOPIC,
            value=event,
            key=user_id,
        )
        logger.info(
            "Published notification booking_id=%s status=%s", booking_id, status.value
        )
    except Exception as exc:
        logger.error(
            "Failed to publish notification booking_id=%s: %s", booking_id, exc
        )


async def _update_status(booking_id: str, status: BookingStatus) -> None:
    async with get_db().acquire() as conn:
        await conn.execute(
            "UPDATE bookings SET status = $1 WHERE id = $2",
            status.value,
            uuid.UUID(booking_id),
        )


async def _check_road_availability(
    booking_id: str,
    user_id: str,
    country_code: str,
    booking_date: date,
    road_ids: List[int],
) -> None:
    """
    Background task: atomically reserve road capacity via road-srv, then update
    the booking status and publish a notification.
    """
    if not road_ids:
        # No roads to check — treat as unconditionally successful.
        logger.info("booking_id=%s has no road_ids, marking SUCCESSFUL", booking_id)
        final_status = BookingStatus.SUCCESSFUL
    else:
        try:
            resp = await get_http().post(
                f"{ROAD_SRV_URL}/roads/increment",
                json={
                    "booking_date": booking_date.isoformat(),
                    "roads": [
                        {"road_id": r, "country_code": country_code} for r in road_ids
                    ],
                },
            )
        except httpx.RequestError as exc:
            logger.error(
                "Could not reach road-srv for booking_id=%s: %s", booking_id, exc
            )
            final_status = BookingStatus.FAILED
        else:
            if resp.status_code == 200 and resp.json().get("status") == "success":
                logger.info("Road capacity reserved for booking_id=%s", booking_id)
                final_status = BookingStatus.SUCCESSFUL
            else:
                logger.info(
                    "Road capacity unavailable for booking_id=%s road_srv_status=%s",
                    booking_id,
                    resp.status_code,
                )
                final_status = BookingStatus.FAILED

    try:
        await _update_status(booking_id, final_status)
        await _publish_notification(user_id, booking_id, final_status)
    except Exception as exc:
        logger.error(
            "Failed to finalise booking_id=%s status=%s: %s",
            booking_id,
            final_status.value,
            exc,
        )


@app.post("/bookings", status_code=202)
async def create_booking(
    request: CreateBookingRequest,
    background_tasks: BackgroundTasks,
    x_user_id: str = Header(
        ..., description="Injected by gateway after authentication"
    ),
    x_request_id: Optional[str] = Header(
        None, description="Client-supplied idempotency key"
    ),
) -> dict:
    """
    Accept a booking request.

    1. If X-Request-Id is provided, return the existing booking for that
       (request_id, user_id) pair if one exists (idempotent retry).
    2. Optionally resolve road_ids via journey-srv (if JOURNEY_SRV_URL is set and
       road_ids were not supplied by the caller).
    3. Persist the booking in PENDING state.
    4. Return 202 Accepted immediately.
    5. In the background: attempt to reserve road capacity via road-srv, then
       transition the booking to SUCCESSFUL or FAILED and emit a notification.
    """
    if x_request_id:
        async with get_db().acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, status FROM bookings WHERE request_id = $1 AND user_id = $2",
                x_request_id,
                x_user_id,
            )
        if existing:
            logger.info(
                "Idempotent retry request_id=%s booking_id=%s",
                x_request_id,
                existing["id"],
            )
            return {"id": str(existing["id"]), "status": existing["status"]}

    road_ids: List[int] = request.road_ids or []

    if not road_ids and JOURNEY_SRV_URL:
        try:
            resp = await get_http().post(
                f"{JOURNEY_SRV_URL}/journeys",
                json={
                    "origin": request.start_location,
                    "destination": request.end_location,
                },
                timeout=30,
            )
            if resp.status_code == 404:
                raise HTTPException(
                    status_code=400, detail="No journey found between those locations"
                )
            if resp.status_code != 201:
                raise HTTPException(status_code=502, detail="Journey service error")
            road_ids = [
                way.get("way_id")
                for way in resp.json().get("way_ids", [])
                if way.get("way_id")
            ]
        except httpx.RequestError as exc:
            logger.error("Could not reach journey-srv: %s", exc)
            raise HTTPException(status_code=502, detail="Journey service unavailable")

    booking_id = str(uuid.uuid4())

    async with get_db().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO bookings
                (id, user_id, status, start_location, end_location, booking_date, country_code, road_ids, request_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            uuid.UUID(booking_id),
            x_user_id,
            BookingStatus.PENDING.value,
            request.start_location,
            request.end_location,
            request.booking_date,
            request.country_code,
            road_ids,
            x_request_id,
        )

    logger.info(
        "Created booking_id=%s user_id=%s status=PENDING", booking_id, x_user_id
    )

    background_tasks.add_task(
        _check_road_availability,
        booking_id,
        x_user_id,
        request.country_code,
        request.booking_date,
        road_ids,
    )

    return {"id": booking_id, "status": BookingStatus.PENDING.value}


@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str) -> dict:
    try:
        booking_uuid = uuid.UUID(booking_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Booking not found")

    async with get_replica_db().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, status, start_location, end_location,
                   booking_date, country_code, road_ids, created_at
            FROM bookings WHERE id = $1
            """,
            booking_uuid,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {
        "id": str(row["id"]),
        "user_id": row["user_id"],
        "status": row["status"],
        "start_location": row["start_location"],
        "end_location": row["end_location"],
        "booking_date": row["booking_date"].isoformat(),
        "country_code": row["country_code"],
        "road_ids": list(row["road_ids"]),
        "created_at": row["created_at"].isoformat(),
    }


@app.get("/bookings")
async def list_bookings(
    x_user_id: Annotated[List[str] | None, Header()] = None,
) -> list:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-ID header is required")

    async with get_replica_db().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, status, start_location, end_location,
                   booking_date, country_code, road_ids, created_at
            FROM bookings WHERE user_id = ANY($1)
            ORDER BY created_at DESC
            """,
            x_user_id,
        )

    return [
        {
            "id": str(row["id"]),
            "user_id": row["user_id"],
            "status": row["status"],
            "start_location": row["start_location"],
            "end_location": row["end_location"],
            "booking_date": row["booking_date"].isoformat(),
            "country_code": row["country_code"],
            "road_ids": list(row["road_ids"]),
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]


@app.post("/bookings/{booking_id}/cancel", status_code=200)
async def cancel_booking(
    booking_id: str,
    x_user_id: str = Header(
        ..., description="Injected by gateway after authentication"
    ),
) -> dict:
    try:
        booking_uuid = uuid.UUID(booking_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Booking not found")

    async with get_db().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, status, booking_date, country_code, road_ids FROM bookings WHERE id = $1",
            booking_uuid,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if row["status"] == BookingStatus.CANCELLED:
        return {"id": booking_id, "status": BookingStatus.CANCELLED}

    if row["status"] == BookingStatus.PENDING:
        raise HTTPException(
            status_code=409, detail="Cannot cancel a booking that is still pending"
        )

    if row["status"] == BookingStatus.SUCCESSFUL and row["road_ids"]:
        try:
            resp = await get_http().post(
                f"{ROAD_SRV_URL}/roads/decrement",
                json={
                    "booking_date": row["booking_date"].isoformat(),
                    "roads": [
                        {"road_id": r, "country_code": row["country_code"]}
                        for r in row["road_ids"]
                    ],
                },
            )
            if resp.status_code != 200:
                logger.error(
                    "road-srv decrement failed for booking_id=%s status=%s",
                    booking_id,
                    resp.status_code,
                )
        except httpx.RequestError as exc:
            logger.error(
                "Could not reach road-srv to decrement booking_id=%s: %s",
                booking_id,
                exc,
            )

    await _update_status(booking_id, BookingStatus.CANCELLED)

    ids = {row["user_id"], x_user_id}
    await asyncio.gather(
        *[
            _publish_notification(user_id, booking_id, BookingStatus.CANCELLED)
            for user_id in ids
        ]
    )

    logger.info("Cancelled booking_id=%s user_id=%s", booking_id, x_user_id)
    return {"id": booking_id, "status": BookingStatus.CANCELLED}


@app.get("/health")
async def health() -> dict:
    try:
        async with get_db().acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB unavailable: {exc}")
