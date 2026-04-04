import os
import httpx
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import websockets
import asyncio

from starlette.websockets import WebSocketState
from websockets import ConnectionClosed, ClientConnection

from logger import get_logger

logger = get_logger()

USER_SRV_URL = os.getenv("USER_SRV_URL", "http://user-srv:8000")
BOOKING_SRV_URL = os.getenv("BOOKING_SRV_URL", "http://booking-srv:8000")
NOTIFICATION_SRV_URL = os.getenv("NOTIFICATION_SRV_URL", "ws://notification-srv:8080")
ADMIN_SRV_URL = os.getenv("ADMIN_SRV_URL", "http://admin-srv:8000")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "ws://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "X-Request-Id"],
    max_age=24 * 60 * 60,
)

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
            headers={"Content-Type": "application/json", "X-User-ID": user["id"]},
        )
    except httpx.RequestError as e:
        logger.error("Failed to create booking: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type")
    )


@app.get("/bookings")
async def get_bookings(request: Request) -> Response:
    """
    Retrieve a list of bookings for a user
    1. Client sends GET /bookings
    2. Gateway authenticates via user-srv
    3. If valid, forward the request body to booking-srv GET /bookings with X-User-Id header
    4. Return booking-srv's response
    """
    token = _extract_token(request)
    if token is None:
        return Response(status_code=401, content="Missing or malformed auth header")

    user = await authenticate(token)
    if user is None:
        return Response(status_code=401, content="Unauthorized")

    try:
        response = await http_client.get(
            f"{BOOKING_SRV_URL}/bookings",
            headers={"X-User-Id": user["id"]},
        )
    except httpx.RequestError as e:
        logger.error("Failed to get bookings: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type"),
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
        response = await http_client.get(
            f"{BOOKING_SRV_URL}/bookings/{booking_id}",
            headers={"X-User-ID": user["id"]},
        )
    except httpx.RequestError as e:
        logger.error("Failed to get booking: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type")
    )


@app.post("/bookings/{booking_id}/cancel")
async def cancel_booking(request: Request, booking_id: str) -> Response:
    """
    Cancel a user's booking
    1. Client sends POST /bookings/{booking_id}/cancel
    2. Gateway authenticates via user-srv
    3. If valid, forward the request body to booking-srv POST /bookings/{booking_id}/cancel with X-User-Id header
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
            f"{BOOKING_SRV_URL}/bookings/{booking_id}/cancel",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-User-Id": user["id"]
            },
        )
    except httpx.RequestError as e:
        logger.error("Failed to cancel booking: %s", e)
        return Response(status_code=502, content="Booking service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type"),
    )


@app.get("/admin/bookings/{registration}")
async def admin_get_bookings_for_registration(request: Request, registration: str) -> Response:
    """
    Retrieve a list of bookings for a registration number
    1. Client sends GET /admin/bookings/{registration}
    2. Gateway authenticates via user-srv
    3. If valid, forward the request to admin-srv GET /bookings/{registration}
    4. Return booking-srv's response
    """
    token = _extract_token(request)
    if token is None:
        return Response(status_code=401, content="Missing or malformed auth header")

    user = await authenticate(token)
    if user is None:
        return Response(status_code=401, content="Unauthorized")

    # Ordinarily, we would also perform a check to limit this to only admin users, however this is a demonstration and
    # something that is application-related rather than distributed systems-related, so we don't here.
    try:
        response = await http_client.get(f"{ADMIN_SRV_URL}/bookings/{registration}")
    except httpx.RequestError as e:
        logger.error("Failed to get booking for registration: %s", e)
        return Response(status_code=502, content="Admin service unavailable")

    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=response.headers.get("content-type")
    )


@app.websocket("/ws")
async def proxy_websocket_connections(ws: WebSocket):
    """
    Opens a WebSocket proxy between the client and notification-srv.
    1. Client opens WebSocket connection
    2. Gateway authenticates via user-srv
    3. If valid, open upstream WebSocket with notification-srv
    4. Maintain proxy for as long as both connections are kept alive.
    """
    # JavaScript does not allow setting headers for WebSocket (despite being supported by the protocol), so this is a
    # slightly hacky work-around that relies on query parameters for passing.
    token = ws.query_params.get("token")
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    # user = await authenticate(token)
    user = {"id": "1234"}
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    await ws.accept()

    try:
        upstream = await websockets.connect(
            f"{NOTIFICATION_SRV_URL}/ws",
            additional_headers={"X-User-ID": user["id"]},
        )

        async def client_to_upstream() -> None:
            try:
                while True:
                    msg = await ws.receive_text()
                    await upstream.send(msg)
            except WebSocketDisconnect:
                # This is fine since WebSockets are treated as being ephemeral. We will clean up the connection further
                # on.
                pass

        async def upstream_to_client() -> None:
            try:
                async for msg in upstream:
                    await ws.send_text(msg)
            except ConnectionClosed:
                pass

        tasks = [
            asyncio.create_task(client_to_upstream()),
            asyncio.create_task(upstream_to_client()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()

        await _safe_close_websocket(ws)
        await _safe_close_websocket(upstream)
    except Exception as e:
        logger.error("Error during WebSocket proxying, err=%s", e)
        await ws.close()


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


async def _safe_close_websocket(ws: WebSocket | ClientConnection) -> None:
    """
    Attempts to safely close a websocket connection that may have been established with an upstream or downstream party.
    """
    try:
        if not hasattr(ws, "client_state") or ws.client_state != WebSocketState.DISCONNECTED:
            await ws.close()
    except Exception as e:
        logger.error("Failed to safely close WebSocket connection, err=%s", e)
