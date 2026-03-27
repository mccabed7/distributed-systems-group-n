import os
import httpx
from fastapi import FastAPI, Request, Response

from logger import get_logger

logger = get_logger()

USER_SRV_URL = os.getenv("USER_SRV_URL", "http://user-srv:8000")
BOOKING_SRV_URL = os.getenv("BOOKING_SRV_URL", "http://booking-srv:8000")

app = FastAPI()

http_client = httpx.AsyncClient()

async def authenticate(token: str) -> dict | None:
    """
    Authenticate a user token by calling user-srv
    Returns the user dict if the token is valid, or None if it isn't
    """
    try:
        resp = await http_client.get(f"{USER_SRV_URL}/users/{token}")
    except httpx.RequestError as e:
        # This covers network errors: user-srv is down, DNS can't resolve, etc.
        logger.error("Failed to reach user-srv: %s", e)
        return None

    if resp.status_code == 404:
        # user-srv says this token doesn't match any user
        logger.info("Authentication failed for token=%s", token)
        return None

    if resp.status_code != 200:
        logger.error("Unexpected response from user-srv: status=%s", resp.status_code)
        return None

    return resp.json()

@app.post("/bookings")
async def create_bookings(request: Request) -> Response:
    """
    Create a booking
    1. Client sends POST /bookings with a token
    2. Gateway authenticates user via user-srv
    3. If valid, forward the request body to booking-srv POST /bookings
    4. Return booking-srv's response
    """
    token = _extract_token(request)
    if token is None:
        return Response(status_code=401, content="Missing or malformed auth header")

    user = await authenticate(token)
    if user is None:
        return Response(status_code=401, content="Unauthorized")

    body = await request.body()

    try:
        response = await http_client.post(
            f"{BOOKING_SRV_URL}/bookings",
            content=body,
            headers={"Content-Type": "application/json"},
        )
    except httpx.RequestError as e:
        logger.error("Failed to create booking: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type")
    )

@app.get("/bookings/{booking_id}")
async def get_booking(request: Request, booking_id: str) -> Response:
    """
    Retrieve a booking by ID
    1. Client sends GET /bookings/{booking_id}
    2. Gateway authenticates user via user-srv
    3. If valid, forward the request body to booking-srv GET /bookings/{booking_id}
    4. Return booking-srv's response
    """
    token = _extract_token(request)
    if token is None:
        return Response(status_code=401, content="Missing or malformed auth header")

    user = await authenticate(token)
    if user is None:
        return Response(status_code=401, content="Unauthorized")

    try:
        response = await http_client.get(f"{BOOKING_SRV_URL}/bookings/{booking_id}")
    except httpx.RequestError as e:
        logger.error("Failed to get booking: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type")
    )

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def _extract_token(request: Request) -> str | None:
    """
    Pull the token out of the Authorization header
    """
    auth_header = request.headers.get("authorization")
    if auth_header is None:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]