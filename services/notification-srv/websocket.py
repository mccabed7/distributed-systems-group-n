import asyncio
from collections import defaultdict
from typing import Set, Dict

import websockets
from logger import get_logger
from websockets.exceptions import ConnectionClosed

import clients

logger = get_logger("websockets")

MAX_CONNECTIONS_PER_USER = 10
MAX_QUEUE_CAPACITY = 100


class WebSocketConnectionPool:
    def __init__(self, redis: clients.RedisClient):
        self._redis = redis
        self._connections: Dict[str, Set[Connection]] = defaultdict(set)
        self._connections_lock = asyncio.Lock()

    async def send(self, user_id: str, message: str) -> None:
        async with self._connections_lock:
            conns = list(self._connections.get(user_id, []))

        if not conns:
            return

        dead = []
        for conn in conns:
            if conn.is_closed():
                dead.append(conn)
                continue

            try:
                await conn.send(message)
            except (Exception,) as e:
                logger.error("Failed to send message, user_id=%s, err=%s", user_id, e)
                dead.append(conn)

        if not dead:
            return

        async with self._connections_lock:
            for conn in dead:
                self._connections[user_id].discard(conn)
                if not self._connections[user_id]:
                    del self._connections[user_id]
                    await self._redis.deregister_user(user_id)

        for conn in dead:
            await conn.close()

    async def serve(self) -> None:
        await websockets.serve(self._handler, "0.0.0.0", 8080)

    async def _handler(self, ws: websockets.ServerConnection) -> None:
        user_id = ws.request.headers.get("X-User-ID")
        if not user_id:
            await ws.close()
            return

        await self._redis.register_user(user_id)
        connection = Connection(ws)
        async with self._connections_lock:
            user_connections = self._connections[user_id]
            if len(user_connections) >= MAX_CONNECTIONS_PER_USER:
                await ws.close()
                return

            self._connections[user_id].add(connection)

        try:
            while True:
                await ws.recv()
        except ConnectionClosed as e:
            logger.error("WebSocket connection closed, user_id=%s, err=%s", user_id, e)
        finally:
            async with self._connections_lock:
                if user_id not in self._connections:
                    return
                self._connections[user_id].discard(connection)
                if not self._connections[user_id]:
                    del self._connections[user_id]
                    await self._redis.deregister_user(user_id)


class Connection:
    def __init__(self, ws: websockets.ServerConnection):
        self._ws = ws
        self._queue = asyncio.Queue(maxsize=MAX_QUEUE_CAPACITY)
        self._closed = False
        self._sender_task = asyncio.create_task(self._sender())

    async def send(self, message: str) -> None:
        if self._closed:
            raise RuntimeError("Connection closed")

        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            raise RuntimeError("Client too slow")

    def is_closed(self) -> bool:
        return self._closed

    async def close(self):
        if self._closed:
            return

        self._closed = True
        self._sender_task.cancel()

        try:
            await self._sender_task
        except asyncio.CancelledError:
            pass

        await self._ws.close()

    async def _sender(self):
        try:
            while True:
                message = await self._queue.get()
                try:
                    await self._ws.send(message)
                except Exception as e:
                    logger.error("Failed to send message, err=%s", e)
                    break
        except asyncio.CancelledError:
            # This might happen during shutdown but is fine
            pass
        finally:
            self._closed = True
