import redis


PROCESSING_TTL = 3_600

class RedisClient:
    def __init__(self, host: str, port: int, pod_id: str):
        self._client = redis.Redis(host=host, port=port, decode_responses=True)
        self._pod_id = pod_id

    def is_message_completed(self, message_id: str) -> bool:
        state = self._client.get(f"message:{message_id}:state")
        return state == "completed"

    def claim_message(self, message_id: str) -> bool:
        return self._client.set(
            f"message:{message_id}:state",
            "processing",
            nx=True,
            ex=PROCESSING_TTL,
        )

    def complete_message(self, message_id: str) -> None:
        return self._client.set(
            f"message:{message_id}:state",
            "completed",
            ex=PROCESSING_TTL,
        )

