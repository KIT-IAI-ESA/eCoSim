import asyncio
import base64
import threading

import websockets
from websockets import ConnectionClosedOK
from websockets.asyncio.client import ClientConnection

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.simulation.renderer.rendering_messages import (
    RawRenderingMessageHandler,
    RenderingMessageType,
    RenderingImageMessage,
    RenderingImageReplyMessage,
)
from ecosim_common.simulation.renderer.rendering_request_headers import RenderingMessageClientHeader
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


class RenderingSocketClient(ShutdownListener):
    _logger = ESPLogger("RenderingSocketClient")

    def __init__(
        self,
        uri: str,
        client_config: ClientConfig,
        renderer_service: SimulationRendererService,
    ):
        self._uri: str = uri
        self._websocket: ClientConnection | None = None
        self._running: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None
        self._renderer_service: SimulationRendererService = renderer_service
        self._client_config = client_config
        self._started_event: threading.Event | None = None
        self._no_sending_in_progress: threading.Event = threading.Event()
        self._no_sending_in_progress.set()
        ShutdownManager().register_listener(self)

    def start(self) -> threading.Event:
        self._started_event = threading.Event()
        self._running.set()
        self._thread = threading.Thread(target=self._run_client, args=(self._uri,))
        self._thread.daemon = True
        self._thread.start()
        return self._started_event

    def _run_client(
        self,
        url: str,
    ) -> None:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)

        try:
            _loop.run_until_complete(self._connect_and_run(url))
        finally:
            _loop.close()

    async def _connect_and_run(
        self,
        url: str,
    ) -> None:
        try:
            RenderingSocketClient._logger.debug("Connecting to %s...", url)
            self._websocket = await websockets.connect(
                url,
                additional_headers=RenderingMessageClientHeader.create_raw(
                    client_id=self._client_config.client_id(),
                ),
                max_size=None,
            )
            RenderingSocketClient._logger.debug("Connecting to %s... success.", url)
            if self._started_event:
                self._started_event.set()
            else:
                RenderingSocketClient._logger.warning("started_event is not set => this may lead to an infinite waiting loop")

            try:
                while self._running.is_set():
                    try:
                        message = RawRenderingMessageHandler(
                            await asyncio.wait_for(self._websocket.recv(), timeout=5.0),
                        )
                    except TimeoutError:
                        continue
                    if message.message_type() == RenderingMessageType.RENDERING_IMAGE:
                        rendering_image_message: RenderingImageMessage | None = None
                        try:
                            self._no_sending_in_progress.clear()
                            rendering_image_message = message.cast(RenderingImageMessage)
                            RenderingSocketClient._logger.debug(
                                "Received %s message for time step %s...",
                                RenderingMessageType.RENDERING_IMAGE.value,
                                rendering_image_message.time_step,
                            )
                            image = self._renderer_service.render_step(rendering_image_message.time_step)
                            content = base64.b64encode(image).decode("utf-8") if image else None
                            await self._websocket.send(
                                RenderingImageReplyMessage(
                                    time_step=rendering_image_message.time_step,
                                    base64=content,
                                ).model_dump_json(),
                            )
                            RenderingSocketClient._logger.debug(
                                "Handled %s message for time step %s... success.",
                                RenderingMessageType.RENDERING_IMAGE.value,
                                rendering_image_message.time_step,
                            )
                        except Exception as e:
                            RenderingSocketClient._logger.error(
                                "Something went wrong sending images of time step %s: %s",
                                rendering_image_message.time_step if rendering_image_message else "N/A",
                                e,
                            )
                        finally:
                            self._no_sending_in_progress.set()
                    else:
                        RenderingSocketClient._logger.warning("Received unprocessable message: %s", message.raw_json())
            except ConnectionClosedOK:
                RenderingSocketClient._logger.debug("received closing connection from server")
            except Exception as e:
                RenderingSocketClient._logger.error("Something went wrong running the rendering socket client: %s", e)
            finally:
                RenderingSocketClient._logger.debug("Reached end - closing socket.")
                if self._websocket:
                    await self._websocket.close()
        except Exception as e:
            RenderingSocketClient._logger.error("Something went wrong connecting to %s: %s", url, e)

    def close(self) -> None:
        if not self._running.is_set():
            return
        RenderingSocketClient._logger.debug("Close was called.")
        self._running.clear()
        if not self._no_sending_in_progress.is_set():
            timeout = 9
            RenderingSocketClient._logger.debug("Sending is currently in progress. Waiting for %s seconds...", timeout)
            success = self._no_sending_in_progress.wait(timeout)
            RenderingSocketClient._logger.debug(
                "Sending is currently in progress. Waited for %s seconds... %s",
                timeout,
                "success" if success else "failed.",
            )
        if self._thread:
            self._thread.join()

    def on_app_shutdown(self) -> None:
        self.close()
