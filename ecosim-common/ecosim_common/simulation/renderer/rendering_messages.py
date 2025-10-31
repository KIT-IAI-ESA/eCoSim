from __future__ import annotations

import json
from enum import Enum
from typing import Any, Type, Dict

from ecosim_common.tech.pydantic.app_base_model import AppBaseModel


class RenderingMessage(AppBaseModel):
    message_type: RenderingMessageType


class RenderingMessageType(Enum):
    RENDERING_IMAGE = "RENDERING_IMAGE"
    RENDERING_IMAGE_REPLY = "RENDERING_IMAGE_REPLY"
    IMAGES_AT_TIME_STEP = "IMAGES_AT_TIME_STEP"


def get_rendering_message_type(message: Any | None) -> RenderingMessageType | None:
    if message is None:
        return None
    try:
        return RenderingMessageType(message["message_type"])
    except ValueError:
        return None


class RenderingImageMessage(RenderingMessage, AppBaseModel):
    message_type: RenderingMessageType = RenderingMessageType.RENDERING_IMAGE
    time_step: int

    @staticmethod
    def from_json(data: Any) -> RenderingImageMessage:
        message_type = get_rendering_message_type(data)
        if not message_type:
            raise ValueError(f"The given json is not a valid rendering message: {data}")
        if message_type != RenderingMessageType.RENDERING_IMAGE:
            raise ValueError(
                f"Wrong message type. Expected {RenderingMessageType.RENDERING_IMAGE.value} and got {message_type}",
            )
        return RenderingImageMessage(
            message_type=message_type,
            time_step=data["time_step"],
        )


class RenderingImageReplyMessage(RenderingMessage, AppBaseModel):
    message_type: RenderingMessageType = RenderingMessageType.RENDERING_IMAGE_REPLY
    time_step: int
    base64: str | None

    @staticmethod
    def from_json(data: Any) -> RenderingImageReplyMessage:
        message_type = get_rendering_message_type(data)
        if not message_type:
            raise ValueError(f"The given json is not a valid rendering message: {data}")
        if message_type != RenderingMessageType.RENDERING_IMAGE_REPLY:
            raise ValueError(
                f"Wrong message type. Expected {RenderingMessageType.RENDERING_IMAGE_REPLY.value} and got {message_type}",
            )
        return RenderingImageReplyMessage(
            message_type=message_type,
            time_step=data["time_step"],
            base64=data["base64"],
        )


class ImagesAtTimeStep(RenderingMessage, AppBaseModel):
    message_type: RenderingMessageType = RenderingMessageType.IMAGES_AT_TIME_STEP
    time_step: int
    # client_id to RenderingImageReplyMessage
    images: Dict[str, RenderingImageReplyMessage]

    @staticmethod
    def from_json(data: Any) -> ImagesAtTimeStep:
        message_type = get_rendering_message_type(data)
        if not message_type:
            raise ValueError(f"The given json is not a valid rendering message: {data}")
        if message_type != RenderingMessageType.IMAGES_AT_TIME_STEP:
            raise ValueError(
                f"Wrong message type. Expected {RenderingMessageType.IMAGES_AT_TIME_STEP.value} and got {message_type}",
            )
        return ImagesAtTimeStep(
            message_type=message_type,
            time_step=data["time_step"],
            images={entry_key: RenderingImageReplyMessage.from_json(entry_value) for entry_key, entry_value in data["images"].items()},
        )


class RawRenderingMessageHandler:
    message_type_to_class = {
        RenderingMessageType.RENDERING_IMAGE: RenderingImageMessage,
        RenderingMessageType.RENDERING_IMAGE_REPLY: RenderingImageReplyMessage,
        RenderingMessageType.IMAGES_AT_TIME_STEP: ImagesAtTimeStep,
    }

    def __init__(
        self,
        raw_message: Any,
    ):
        try:
            self._raw_json: Any = json.loads(raw_message)
        except json.decoder.JSONDecodeError:
            self._raw_json = None
        self._message_type: RenderingMessageType | None = get_rendering_message_type(self._raw_json)

    def message_type(self) -> RenderingMessageType | None:
        return self._message_type

    def raw_json(self) -> Any:
        return self._raw_json

    def cast[T: RenderingMessage](
        self,
        message_class: Type[T],
    ) -> T:
        if not issubclass(message_class, RenderingMessage):
            raise TypeError("message_class must be a subclass of RenderingMessage")
        if self._message_type is None:
            raise ValueError("Message type could not be determined from raw message")
        if RawRenderingMessageHandler.message_type_to_class[self._message_type] != message_class:
            raise ValueError(
                f"Message type '{self._message_type}' does not match casting type '{message_class.__name__}'.",
            )
        match self._message_type:
            case RenderingMessageType.RENDERING_IMAGE:
                return RenderingImageMessage.from_json(
                    self._raw_json,
                )  # type: ignore  # at this point the type is known so we can ignore the mypy error
            case RenderingMessageType.RENDERING_IMAGE_REPLY:
                return RenderingImageReplyMessage.from_json(
                    self._raw_json,
                )  # type: ignore  # at this point the type is known so we can ignore the mypy error
            case RenderingMessageType.IMAGES_AT_TIME_STEP:
                return ImagesAtTimeStep.from_json(
                    self._raw_json,
                )  # type: ignore  # at this point the type is known so we can ignore the mypy error
        raise ValueError(f"Unsupported message type {self._message_type}")
