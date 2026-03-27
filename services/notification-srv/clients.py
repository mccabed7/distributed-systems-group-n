import redis


PROCESSING_TTL = 3_600

class RedisClient:
    def __init__(self, host: str, port: int, pod_id: str):
        self._client = redis.asyncio.Redis(host=host, port=port, decode_responses=True)
        self._pod_id = pod_id

    async def is_message_completed(self, message_id: str) -> bool:
        state = await self._client.get(f"message:{message_id}:state")
        return state == "completed"

    async def claim_message(self, message_id: str) -> bool:
        return await self._client.set(
            f"message:{message_id}:state",
            "processing",
            nx=True,
            ex=PROCESSING_TTL,
        )

    async def complete_message(self, message_id: str) -> None:
        return await self._client.set(
            f"message:{message_id}:state",
            "completed",
            ex=PROCESSING_TTL,
        )

