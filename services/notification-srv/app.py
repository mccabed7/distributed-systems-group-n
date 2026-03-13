from logger import get_logger
import os
from consumers import NotificationConsumer

logger = get_logger()

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
TOPIC = os.getenv("KAFKA_TOPIC")
GROUP_ID = os.getenv("KAFKA_GROUP_ID")


def main() -> None:
    if not (BOOTSTRAP_SERVERS and TOPIC and GROUP_ID):
        logger.error(
            "Missing configuration, ensure KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC and KAFKA_GROUP_ID environment variables are set")
        exit(1)

    logger.info("Starting consumer")
    logger.info("Kafka bootstrap servers: %s", BOOTSTRAP_SERVERS)
    logger.info("Topic: %s", TOPIC)

    consumer = NotificationConsumer(
        topic=TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID
    )
    consumer.connect()
    consumer.consume()


if __name__ == "__main__":
    main()
