from kafka import KafkaConsumer
from pydantic import ValidationError
import messages
from logger import get_logger
from typing import AnyStr

logger = get_logger("consumers")


class NotificationConsumer:
    _consumer: KafkaConsumer

    def __init__(self, topic: str, bootstrap_servers: str, group_id: str):
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id

    def connect(self) -> None:
        logger.info("Attempting to connect to Kafka broker")
        self._consumer = KafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda v: v.decode("utf-8"),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )
        logger.info("Connected to Kafka broker")

    def consume(self) -> None:
        for message in self._consumer:
            logger.info(
                "Received message topic=%s partition=%s offset=%s key=%s",
                message.topic,
                message.partition,
                message.offset,
                message.key,
            )

            self.process_message(message.key, message.value)

    def process_message(self, key: str, raw_message: AnyStr) -> None:
        try:
            message = messages.parse_message(raw_message)
        except ValidationError as e:
            logger.error("Failed to parse message, key=%s, err=%s", key, e)
            return

        if message.delivery_type == messages.DeliveryType.PUSH.value:
            logger.info("Message is PUSH notification, key=%s", key)
        elif message.delivery_type == messages.DeliveryType.EMAIL.value:
            logger.info("Message is EMAIL notification, key=%s", key)
