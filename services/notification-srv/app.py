import json
import logging
import os
from kafka import KafkaConsumer

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("notification-srv")
logger.setLevel(logging.INFO)

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

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: v.decode("utf-8"),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
    )

    for message in consumer:
        payload = message.value

        try:
            payload = json.loads(payload)
        except Exception:
            pass

        logger.info(
            "Received message topic=%s partition=%s offset=%s key=%s payload=%s",
            message.topic,
            message.partition,
            message.offset,
            message.key,
            payload,
        )


if __name__ == "__main__":
    main()
