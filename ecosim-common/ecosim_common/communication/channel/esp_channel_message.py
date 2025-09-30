from abc import ABC, abstractmethod
from typing import Type, Any

from ecosim_common.communication.channel.message_data import MESSAGE_DATA
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.correlation_id import CorrelationId


class ESPChannelMessage(ABC):

    @abstractmethod
    def type(self) -> MessageType:
        pass

    @abstractmethod
    def payload(self,
                clazz: Type[MESSAGE_DATA] | None = None,
                ) -> MESSAGE_DATA | Any:
        """
        :param clazz: the type the payload should be transformed to
        :return: returns either the transformed payload or (if the parameter is not given) the raw payload
        """
        pass

    @abstractmethod
    def correlation_id(self) -> CorrelationId:
        pass
