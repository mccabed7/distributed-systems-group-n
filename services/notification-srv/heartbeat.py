import asyncio
from logger import get_logger

from clients import RedisClient

logger = get_logger("heartbeat")


class Heartbeat:
    def __init__(self, client: RedisClient):
        self._client = client
        self._running = True

    async def run(self) -> None:
        while self._running:
            logger.info("Registering Redis heartbeat")
            await self._client.heartbeat()
            await asyncio.sleep(10)

    def stop(self):
        self._running = False
