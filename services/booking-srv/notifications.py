from __future__ import annotations

from typing import Annotated, Union, Literal, Optional

from aiokafka import AIOKafkaProducer
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from enum import Enum


class DeliveryType(str, Enum):
    PUSH = "PUSH"
    EMAIL = "EMAIL"


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delivery_type: DeliveryType
    user_id: str
    message_id: str
    content: str


class PushMessage(Message):
    delivery_type: Literal[DeliveryType.PUSH] = DeliveryType.PUSH.value


class EmailMessage(Message):
    delivery_type: Literal[DeliveryType.EMAIL] = DeliveryType.EMAIL.value
    email: EmailStr
    subject: str


Notification = Annotated[Union[PushMessage, EmailMessage], Field(discriminator="delivery_type")]


class NotificationClient:
    _producer: Optional[AIOKafkaProducer]

    def __init__(self, bootstrap_servers: str, topic: str, pod_id: str):
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._pod_id = pod_id

    async def start(self) -> None:
        if not self._producer:
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._pod_id,
            acks="all",
        )
        await self._producer.start()

    async def stop(self) -> None:
        if not self._producer:
            return

        await self._producer.stop()
        self._producer = None

    async def send(self, booking_id: str, notification: Notification) -> None:
        if not self._producer:
            raise RuntimeError("Producer has not been started")

        await self._producer.send_and_wait(
            topic=self._topic,
            key=booking_id,
            value=notification.model_dump_json(),
        )
