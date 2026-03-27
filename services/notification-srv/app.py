from logger import get_logger
import os
from consumers import NotificationConsumer
import clients

logger = get_logger()

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
TOPIC = os.getenv("KAFKA_TOPIC")
GROUP_ID = os.getenv("KAFKA_GROUP_ID")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
HOSTNAME = os.getenv("HOSTNAME")


def main() -> None:
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

    consumer = NotificationConsumer(
        topic=TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        redis=redis_client,
    )
    consumer.connect()
    consumer.consume()


if __name__ == "__main__":
    main()
