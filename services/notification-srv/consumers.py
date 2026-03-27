from aiokafka import AIOKafkaConsumer
from pydantic import ValidationError
import messages
from logger import get_logger
from typing import AnyStr
import clients

logger = get_logger("consumers")


class NotificationConsumer:
    _consumer: AIOKafkaConsumer

    def __init__(self, topic: str, bootstrap_servers: str, group_id: str, redis: clients.RedisClient):
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._redis = redis

    def connect(self) -> None:
        logger.info("Attempting to connect to Kafka broker")
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda v: v.decode("utf-8"),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )
        logger.info("Connected to Kafka broker")

    async def consume(self) -> None:
        await self._consumer.start()
        try:
            async for message in self._consumer:
                logger.info(
                    "Received message topic=%s partition=%s offset=%s key=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                    message.key,
                )

                await self.process_message(message.key, message.value)
        finally:
            await self._consumer.stop()

    async def process_message(self, key: str, raw_message: AnyStr) -> None:
        try:
            message = messages.parse_message(raw_message)
        except ValidationError as e:
            logger.error("Failed to parse message, key=%s, err=%s", key, e)
            return

        if await self._redis.is_message_completed(message.message_id):
            logger.info("Message [%s] is already completed", message.message_id)
            await self._consumer.commit()
            return

        if not await self._redis.claim_message(message.message_id):
            logger.info("Message [%s] could not be claimed", message.message_id)
            # Another consumer may have crashed after accepting the message. In this case, duplicate messages are
            # better than failing to deliver entirely, so we continue to process here.
            if await self._redis.is_message_completed(message.message_id):
                logger.info("Message [%s] is already completed", message.message_id)
                await self._consumer.commit()
                return

        if message.delivery_type == messages.DeliveryType.PUSH.value:
            logger.info("Message is PUSH notification, key=%s", key)
        elif message.delivery_type == messages.DeliveryType.EMAIL.value:
            logger.info("Message is EMAIL notification, key=%s", key)

        await self._redis.complete_message(message.message_id)
        await self._consumer.commit()
        logger.info("Finished processing message [%s]", message.message_id)
