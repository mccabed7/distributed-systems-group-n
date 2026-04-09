import os
import uuid
from contextlib import asynccontextmanager
import datetime
from typing import AsyncIterator

import asyncpg
import jose
from asyncpg import UniqueViolationError
from fastapi import FastAPI, Request, HTTPException
from jose import jwt
from passlib.context import CryptContext

import schema
from logger import get_logger

logger = get_logger()

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT"))
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS"))

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db_pool = await asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DATABASE,
    )

    _app.state.db_pool = db_pool

    try:
        yield
    finally:
        await db_pool.close()


app = FastAPI(lifespan=lifespan)


@app.post("/login", response_model=schema.LoginResponse)
async def login(request: Request, payload: schema.LoginRequest) -> schema.LoginResponse:
    """
    Logs a user in.
    1. Fetch the user from the db
    2. If present, verify the password
    3. If successful, issue a new JWT token
    """
    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, username, password
            FROM users
            WHERE username = $1
            """,
            payload.username
        )

    if not row:
        logger.error("No user found, username=%s", payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not password_context.verify(payload.password, row["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    claims = {
        "sub": str(row["id"]),
        "username": payload.username,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(claims, JWT_SECRET, JWT_ALGORITHM)

    return schema.LoginResponse(
        id=row["id"],
        username=payload.username,
        token=token,
    )


@app.post("/register", response_model=schema.RegisterResponse)
async def register(request: Request, payload: schema.RegisterRequest) -> schema.RegisterResponse:
    """
    Registers a user
    1. Hash the password and generate an ID
    2. Attempt to insert the user into the DB
    3. Return the user ID if successful, otherwise return 400 as a user already exists
    """
    password = password_context.hash(payload.password)
    user_id = uuid.uuid4()

    try:
        async with request.app.state.db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO users (id, username, password)
                    VALUES ($1, $2, $3)
                    """,
                    str(user_id),
                    payload.username,
                    password,
                )
    except UniqueViolationError as e:
        logger.error("Username already exists: username=%s, err=%s", payload.username, e)
        raise HTTPException(status_code=400, detail="Username already exists")

    return schema.RegisterResponse(id=user_id)


@app.get("/users/{token}", response_model=schema.UserResponse)
async def get_user_by_token(request: Request, token: str) -> schema.UserResponse:
    """
    Finds a user by their token.
    1. Decode the token.
    2. If successful, lookup the user
    3. If successful, return the user, otherwise return an error.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, JWT_ALGORITHM)
    except jose.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    username = payload.get("username")

    if not user_id or not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    async with request.app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, username
            FROM users
            WHERE id = $1 AND username = $2
            """,
            user_id,
            username,
        )

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return schema.UserResponse(
        id=user_id,
        username=username,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
