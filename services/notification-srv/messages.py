from __future__ import annotations

from typing import AnyStr, Annotated, Union, Literal

from pydantic import BaseModel, Field, ConfigDict, TypeAdapter, EmailStr
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


Notification = Annotated[Union[PushMessage, EmailMessage], Field(discriminator="delivery_type")]


def parse_message(payload: AnyStr) -> Notification:
    adapter = TypeAdapter(Notification)
    return adapter.validate_json(payload)
