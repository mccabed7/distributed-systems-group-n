from aiokafka import AIOKafkaConsumer
from redis.asyncio import Redis
from pydantic import ValidationError
import messages
from logger import get_logger
from typing import AnyStr
import clients
from websocket import WebSocketConnectionPool

logger = get_logger("consumers")


class NotificationConsumer:
    _consumer: AIOKafkaConsumer

    def __init__(self, topic: str, bootstrap_servers: str, group_id: str, pod_id: str, redis: clients.RedisClient):
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._pod_id = pod_id
        self._redis = redis

    def connect(self) -> None:
        logger.info("Attempting to connect to Kafka broker")
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._pod_id,
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
                    "Received Kafka message topic=%s partition=%s offset=%s key=%s",
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
            logger.error("Failed to parse Kafka message, key=%s, err=%s", key, e)
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
            logger.info("Message is PUSH notification, message_id=%s", message.message_id)
            await self._redis.fanout_publish_message(message.user_id, raw_message)
        elif message.delivery_type == messages.DeliveryType.EMAIL.value:
            logger.info("Message is EMAIL notification, key=%s", key)

        await self._redis.complete_message(message.message_id)
        await self._consumer.commit()
        logger.info("Finished processing message [%s]", message.message_id)


class PushNotificationConsumer:
    def __init__(self, ws_pool: WebSocketConnectionPool, host: str, port: int, pod_id: str):
        self._ws_pool = ws_pool
        self._subscriber = Redis(host=host, port=port).pubsub()
        self._pod_id = pod_id

    async def connect(self) -> None:
        await self._subscriber.subscribe(f"pod:{self._pod_id}")

    async def consume(self) -> None:
        async for raw_message in self._subscriber.listen():
            try:
                message = messages.parse_message(raw_message["data"])
            except ValidationError as e:
                logger.error("Failed to parse push notification, err=%s", e)
                continue

            if message.delivery_type != messages.DeliveryType.PUSH.value:
                logger.error("Message [%s] has unexpected delivery_type: %s", message.message_id,
                             message.delivery_type.value)
                continue

            logger.info("Received Redis message, message_id=%s", message.message_id)
            send_message = f'{{"message_id":"{message.message_id}","content":"{message.content}"}}'
            await self._ws_pool.send(message.user_id, send_message)
