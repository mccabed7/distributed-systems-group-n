import asyncio

from logger import get_logger
import os
from consumers import NotificationConsumer, PushNotificationConsumer
import clients
from heartbeat import Heartbeat
import websocket

logger = get_logger()

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
TOPIC = os.getenv("KAFKA_TOPIC")
GROUP_ID = os.getenv("KAFKA_GROUP_ID")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
HOSTNAME = os.getenv("HOSTNAME")


async def main() -> None:
    if not (BOOTSTRAP_SERVERS and TOPIC and GROUP_ID and REDIS_HOST and REDIS_PORT and HOSTNAME):
        logger.error(
            "Missing configuration, ensure KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_GROUP_ID, "
            "REDIS_HOST, REDIST_PORT and HOSTNAME environment variables are set",
        )
        exit(1)

    logger.info("Starting consumer")
    logger.info("Kafka bootstrap servers: %s", BOOTSTRAP_SERVERS)
    logger.info("Topic: %s", TOPIC)

    redis_client = clients.RedisClient(REDIS_HOST, REDIS_PORT, pod_id=HOSTNAME)
    logger.info("Connected to redis @ %s:%d", REDIS_HOST, REDIS_PORT)

    heartbeat = Heartbeat(redis_client)
    ws_pool = websocket.WebSocketConnectionPool(redis_client)

    push_notifications = PushNotificationConsumer(ws_pool, REDIS_HOST, REDIS_PORT, pod_id=HOSTNAME)
    await push_notifications.connect()

    consumer = NotificationConsumer(
        topic=TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        pod_id=HOSTNAME,
        redis=redis_client,
    )
    consumer.connect()

    await asyncio.gather(
        heartbeat.run(),
        push_notifications.consume(),
        consumer.consume(),
        ws_pool.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
