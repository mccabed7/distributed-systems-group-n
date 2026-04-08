import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
import httpx
from fastapi import FastAPI, Request, Response

import schema
from logger import get_logger

logger = get_logger()

BOOKING_SRV_URL = os.getenv("BOOKING_SRV_URL")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT"))
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db_pool = await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DATABASE,
    )
    http_client = httpx.AsyncClient()

    _app.state.db_pool = db_pool
    _app.state.http_client = http_client

    try:
        yield
    finally:
        await http_client.aclose()
        await db_pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/bookings/{registration}")
async def get_bookings_for_registration(request: Request, registration: str) -> Response:
    """
    Looks up bookings for the given registration.
    1. Find all users under the given registration, exiting early if none exist
    2. Ask booking-srv for all bookings with the given user IDs
    3. Return the response to the user
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id
                FROM user_registrations
                WHERE registration_id = $1
                """,
                registration,
            )
            users = [str(row["user_id"]) for row in rows]

        logger.info("Users: %s", users)

        if not users:
            return Response(
                status_code=200,
                content=b'[]',
                media_type="application/json"
            )

        response = await request.app.state.http_client.get(
            f"{BOOKING_SRV_URL}/bookings",
            headers=[("X-User-Id", user_id) for user_id in users],
        )
    except httpx.RequestError as e:
        logger.error("Failed to list bookings for registration: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type"),
    )


@app.post("/registrations")
async def create_registration(request: Request, payload: schema.CreateRegistrationRequest) -> Response:
    async with request.app.state.db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO user_registrations (user_id, registration_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, registration_id) DO NOTHING
                """,
                payload.user_id,
                payload.registration_id,
            )
    return Response(status_code=201)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
