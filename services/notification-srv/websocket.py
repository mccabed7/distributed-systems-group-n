import asyncio
from collections import defaultdict
from typing import Set, Dict

import websockets
from logger import get_logger
from websockets.exceptions import ConnectionClosed

import clients

logger = get_logger("websockets")


class WebSocketConnectionPool:
    def __init__(self, redis: clients.RedisClient):
        self._redis = redis
        self._connections: Dict[str, Set[websockets.ServerConnection]] = defaultdict(set)
        self._connections_lock = asyncio.Lock()

    async def send(self, user_id: str, message: str) -> None:
        async with self._connections_lock:
            conns = list(self._connections.get(user_id, []))

        if not conns:
            return

        dead = []
        for conn in conns:
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

    async def serve(self) -> None:
        await websockets.serve(self._handler, "0.0.0.0", 8080)

    async def _handler(self, ws: websockets.ServerConnection) -> None:
        user_id = "123"  # TODO: actually get user_id somehow!

        if not user_id:
            await ws.close()
            return

        async with self._connections_lock:
            self._connections[user_id].add(ws)
        await self._redis.register_user(user_id)

        try:
            while True:
                await ws.recv()
        except ConnectionClosed as e:
            logger.error("WebSocket connection closed, user_id=%s, err=%s", user_id, e)
        finally:
            async with self._connections_lock:
                if user_id not in self._connections:
                    return
                self._connections[user_id].discard(ws)
                if not self._connections[user_id]:
                    del self._connections[user_id]
                    await self._redis.deregister_user(user_id)
