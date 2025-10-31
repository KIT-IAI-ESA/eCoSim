import asyncio
import dataclasses
from collections import defaultdict
from threading import RLock
from typing import Dict, Set

from ecosim_common.simulation.renderer.rendering_messages import RenderingImageReplyMessage
from ecosim_common.simulation.renderer.rendering_request_headers import RenderingMessageClientHeader
from ecosim_common.tech.logger.logger import ESPLogger

_image_cache_logger = ESPLogger("ImageCache")


@dataclasses.dataclass(frozen=True)
class ImageCache:
    _image_cache: Dict[int, Dict[str, RenderingImageReplyMessage]] = dataclasses.field(
        default_factory=lambda: defaultdict(lambda: defaultdict(dict)),
    )
    _events: Dict[int, asyncio.Event] = dataclasses.field(
        default_factory=lambda: defaultdict(asyncio.Event),
    )
    _expected_clients: Dict[int, Set[str]] = dataclasses.field(
        default_factory=lambda: defaultdict(set),
    )

    _lock: RLock = dataclasses.field(default_factory=RLock)

    def put(
        self,
        client_header: RenderingMessageClientHeader,
        reply: RenderingImageReplyMessage,
    ):
        _image_cache_logger.debug(f"New image for time step {reply.time_step} from {client_header.client_id}")
        with self._lock:
            self._image_cache[reply.time_step][client_header.client_id] = reply
            if self.contains(reply.time_step, self._expected_clients[reply.time_step]):
                self._events[reply.time_step].set()

    def contains(
        self,
        time_step: int,
        client_ids: Set[str],
    ) -> bool:
        # the check for the key ensures that the corresponding dict exists so we can skip the lock for the actual call
        if not self._image_cache.keys().__contains__(time_step):
            return False
        return all(key in self._image_cache[time_step].keys() for key in client_ids)

    async def wait_for_images(
        self,
        time_step: int,
        client_ids: Set[str],
    ):
        if self.contains(time_step, client_ids):
            return
        with self._lock:
            self._expected_clients[time_step] = client_ids
        await self._events[time_step].wait()

    def get(
        self,
        time_step: int,
    ) -> Dict[str, RenderingImageReplyMessage]:
        # the check for the key ensures that the corresponding dict exists so we can skip the lock for the actual call
        if not self._image_cache.keys().__contains__(time_step):
            return {}
        return self._image_cache[time_step]
