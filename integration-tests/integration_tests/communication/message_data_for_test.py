from __future__ import annotations
from dataclasses import dataclass

from ecosim_common.communication.channel.message_data import MessageData


@dataclass(frozen=True)
class MessageDataForTest(MessageData):

    string: str = "Hello World"
    integer: int = 12345
