import time
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from logger import get_logger
from typing import Optional

logger = get_logger("consumers")


class NotificationConsumer:
    _consumer: KafkaConsumer

    def __init__(self, topic: str, bootstrap_servers: str, group_id: str):
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id

    def connect(self) -> None:
        attempts = 0
        failure: Optional[NoBrokersAvailable] = None
        while attempts < 5:
            try:
                attempts += 1
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
                return
            except NoBrokersAvailable as e:
                failure = e
                logger.error("Failed to connect to Kafka broker, e=%s", e)
                time.sleep(3)

        if failure:
            raise failure

    def consume(self) -> None:
        for message in self._consumer:
            logger.info(
                "Received message topic=%s partition=%s offset=%s key=%s payload=%s",
                message.topic,
                message.partition,
                message.offset,
                message.key,
                message.value,
            )
