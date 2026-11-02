import queue
import threading

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage

BOUND_IN_SECONDS = 15


def listen_blocking_in_background(channel: ESPChannel, timeout_in_seconds: int | None = None) -> queue.Queue[ESPChannelMessage | Exception | None]:
    outcome: queue.Queue[ESPChannelMessage | Exception | None] = queue.Queue()
    threading.Thread(target=_listen_into, args=(outcome, channel, timeout_in_seconds), daemon=True).start()
    return outcome


def listen_blocking_bounded(channel: ESPChannel, timeout_in_seconds: int | None = None) -> ESPChannelMessage | None:
    # a hang raises queue.Empty, which pytest.raises(TimeoutError) does not accept
    result = listen_blocking_in_background(channel=channel, timeout_in_seconds=timeout_in_seconds).get(timeout=BOUND_IN_SECONDS)
    if isinstance(result, Exception):
        raise result
    return result


def _listen_into(outcome: queue.Queue[ESPChannelMessage | Exception | None], channel: ESPChannel, timeout_in_seconds: int | None) -> None:
    try:
        outcome.put(channel.listen_blocking(timeout_in_seconds=timeout_in_seconds))
    except Exception as error:
        outcome.put(error)
