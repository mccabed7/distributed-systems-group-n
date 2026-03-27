import redis

PROCESSING_TTL = 3_600


class RedisClient:
    def __init__(self, host: str, port: int, pod_id: str):
        self._client = redis.asyncio.Redis(host=host, port=port, decode_responses=True)
        self._pod_id = pod_id

    async def heartbeat(self) -> None:
        await self._client.set(f"pod:{self._pod_id}:alive", "1", ex=30)

    async def register_user(self, user_id: str) -> None:
        await self._client.sadd(f"user:{user_id}:pods", self._pod_id)

    async def deregister_user(self, user_id: str) -> None:
        await self._client.srem(f"user:{user_id}:pods", self._pod_id)

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

    async def fanout_publish_message(self, user_id: str, content: str) -> None:
        pods = await self._client.smembers(f"user:{user_id}:pods")
        alive = []
        for pod in pods:
            if await self._client.exists(f"pod:{pod}:alive"):
                alive.append(pod)
            else:
                await self._client.srem(f"user:{user_id}:pods", pod)

        for pod in alive:
            await self._client.publish(f"pod:{pod}", content)
