from __future__ import annotations

from enum import Enum


class ChannelEndpoint(Enum):
    """
    Which of the two ends of a channel this is: the one that accepted the connection or the one that opened it.

    ATTENTION: a 'distributed.Queue' name is a cluster wide key, so it has to name the *owner* of a queue
    and never the role that queue plays for whoever asks. Both endpoints run the same code, so a relative
    name - 'my inbox' - would be the same string on both sides, which is one shared queue again. The
    relative view belongs in the code instead, see 'DaskChannel._inbox' and 'DaskChannel._peer_inbox'.
    """

    LISTENER = "listener"
    CONNECTOR = "connector"

    def peer(self) -> ChannelEndpoint:
        if self is ChannelEndpoint.LISTENER:
            return ChannelEndpoint.CONNECTOR
        return ChannelEndpoint.LISTENER

    def inbox_name(self, connection_id: str) -> str:
        """The queue this endpoint reads - and, seen from the other side, the one the peer writes into."""
        return f"{connection_id}-{self.value}-inbox"
