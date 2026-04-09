import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from asyncpg import UniqueViolationError
from fastapi import FastAPI, Request, HTTPException
from passlib.context import CryptContext

import schema
from logger import get_logger

logger = get_logger()

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT"))
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
