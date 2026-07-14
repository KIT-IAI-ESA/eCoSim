import asyncio
import threading
from typing import Dict, override

import websockets
from ecosim_common.simulation.renderer.rendering_messages import (
    ImagesAtTimeStep,
    RawRenderingMessageHandler,
    RenderingImageMessage,
    RenderingImageReplyMessage,
    RenderingMessageType,
)
from ecosim_common.simulation.renderer.rendering_request_headers import RenderingMessageClientHeader
from ecosim_common.tech.atomic.atomic_integer import AtomicInteger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_server.simulation.rendering.image_cache import ImageCache
from websockets import ServerConnection
from websockets.asyncio.server import Server


class RenderingSocket(ShutdownListener):
    _logger = ESPLogger("RenderingSocket")

    def __init__(
        self,
        host: str,
        port: int,
    ):
        self._host: str = host
        self._port: int = port
        self._image_receiver_socket: ServerConnection | None = None
        self._connected_simulators: Dict[str, ServerConnection] = {}
        self._connected_simulator_ids: set[str] = set()
        self._server: Server | None = None
        self._running: threading.Event = threading.Event()
        self._clients_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._image_cache: ImageCache = ImageCache()
        self._started_event: threading.Event | None = None
        self._finished_event: threading.Event | None = None
        self._no_sending_in_progress: threading.Event = threading.Event()
        self._no_sending_in_progress.set()
        self._currently_sending_processes: AtomicInteger = AtomicInteger.thread(0)
        ShutdownManager().register_listener(self)

    def start(self) -> threading.Event:
        self._started_event = threading.Event()
        self._running.set()
        self._clients_thread = threading.Thread(target=self._run_socket, args=(self._host, self._port))
        self._clients_thread.daemon = True
        self._clients_thread.start()
        return self._started_event

    def _run_socket(
        self,
        host: str,
        port: int,
    ) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_run(host, port))
        if self._started_event:
            self._started_event.set()
        else:
            RenderingSocket._logger.warning(
                "started_event does not exist => this may result in an infinite waiting cycle for a listener",
            )
        self._loop.run_forever()

    async def _connect_and_run(
        self,
        host: str,
        port: int,
    ) -> None:
        RenderingSocket._logger.debug(f"Open websocket on {host}:{port}...")
        self._server = await websockets.serve(self._handle_clients, self._host, self._port, max_size=None)
        RenderingSocket._logger.debug(f"Open websocket on {host}:{port}... success.")

    def close(self) -> None:
        if not self._running.is_set():
            return
        self._finished_event = threading.Event()
        self._running.clear()
        timeout = 9
        RenderingSocket._logger.debug(
            f"Waiting for {timeout} seconds to finish open sending processes (count: {self._currently_sending_processes.value}). "
            + f"Sending in progress: {not self._no_sending_in_progress.is_set()}.",
        )
        sending_finished = self._no_sending_in_progress.wait(timeout)  # permit a graceful shutdown within timeout
        if not sending_finished:
            RenderingSocket._logger.debug(
                f"Socket was triggered to shut down. The open sending processes ({self._currently_sending_processes.value}) could not finish "
                + f"within timeout ({timeout}s) => force closing the socket (this may result in an unhandled exception).",
            )
        else:
            RenderingSocket._logger.debug(
                f"Waiting for {timeout} seconds to finish open sending processes (count: {self._currently_sending_processes.value}) ... success.",
            )
        if self._server:
            self._server.close()
            asyncio.run_coroutine_threadsafe(self._server.wait_closed(), self._loop or asyncio.get_event_loop())

    async def _handle_clients(
        self,
        connection: ServerConnection,
    ) -> None:
        client_header = RenderingMessageClientHeader.of_connection(connection)
        RenderingSocket._logger.debug(f"Client {client_header.client_id} connected")
        if client_header.is_simulator():
            if client_header.client_id in self._connected_simulators:
                previous_connection = self._connected_simulators[client_header.client_id]
                RenderingSocket._logger.warning(
                    f"{client_header.client_id} socket is already taken - this will override and close the previous one.",
                )
                await previous_connection.close()
            self._connected_simulators[client_header.client_id] = connection
            self._connected_simulator_ids.add(client_header.client_id)
        else:
            if self._image_receiver_socket is not None:
                RenderingSocket._logger.warning(
                    "Image receiver socket is already taken - this will override and close the previous one.",
                )
                await self._image_receiver_socket.close()
            self._image_receiver_socket = connection

        try:
            while self._running.is_set():
                message = RawRenderingMessageHandler(await connection.recv())
                if client_header.is_simulator():
                    await self._handle_simulator_message(message, client_header)
                else:
                    await self._handle_sim_control_message(message, client_header)
        except websockets.exceptions.ConnectionClosed:
            RenderingSocket._logger.info(f"Client {client_header.client_id} disconnected")
        finally:
            self._connected_simulators.pop(client_header.client_id, None)
            self._connected_simulator_ids.discard(client_header.client_id)

    async def _handle_simulator_message(
        self,
        message: RawRenderingMessageHandler,
        client_header: RenderingMessageClientHeader,
    ) -> None:
        if message.message_type() == RenderingMessageType.RENDERING_IMAGE_REPLY:
            reply = message.cast(RenderingImageReplyMessage)
            RenderingSocket._logger.debug(
                f"From {client_header.client_id} received {RenderingMessageType.RENDERING_IMAGE_REPLY.value} message for time step {reply.time_step}",
            )
            self._image_cache.put(client_header, reply)
        else:
            RenderingSocket._logger.debug(f"From {client_header.client_id}: {message}")

    async def _handle_sim_control_message(
        self,
        message: RawRenderingMessageHandler,
        client_header: RenderingMessageClientHeader,
    ) -> None:
        if message.message_type() == RenderingMessageType.RENDERING_IMAGE:
            request = message.cast(RenderingImageMessage)
            RenderingSocket._logger.debug(
                f"From {client_header.client_id} received {RenderingMessageType.RENDERING_IMAGE.value} message for time step {request.time_step}",
            )
            self.request_and_send_images(request.time_step)
        else:
            RenderingSocket._logger.debug(f"From {client_header.client_id}: {message}")

    def request_and_send_images(
        self,
        time_step: int,
    ) -> threading.Event:
        RenderingSocket._logger.debug(
            f"request_and_send_images triggered for time_step {time_step} in thread {threading.current_thread().name}",
        )
        end_event = threading.Event()
        if self._loop is None:
            RenderingSocket._logger.error(
                f"request_and_send_images triggered for time_step {time_step} but there is no event loop => ignoring this request.",
            )
            end_event.set()
            return end_event
        asyncio.run_coroutine_threadsafe(
            self._request_images_and_send_images(time_step, end_event),
            self._loop,
        )
        return end_event

    async def _request_images_and_send_images(
        self,
        time_step: int,
        end_event: threading.Event,
    ) -> None:
        if not self._running.is_set():
            RenderingSocket._logger.warning(
                f"Requesting images for time request_images_and_send_images {time_step} but socket is not running (anymore) => "
                + "this request will be ignored.",
            )
            end_event.set()
            return
        RenderingSocket._logger.debug(
            f"Processing request for time_step {time_step} in thread {threading.current_thread().name}",
        )
        try:
            self._no_sending_in_progress.clear()
            self._currently_sending_processes.inc()
            if self._image_cache.contains(time_step, self._connected_simulator_ids):
                RenderingSocket._logger.debug(
                    f"Image cache contains already all needed images at time step {time_step} for {self._connected_simulator_ids} -> "
                    + "no need to query the clients.",
                )
            elif not self._connected_simulators:
                RenderingSocket._logger.warning("No clients connected, that could serve an image")
                return
            else:
                RenderingSocket._logger.debug(f"Requesting image at time_step {time_step}")
                try:
                    request = RenderingImageMessage(time_step=time_step).model_dump_json()
                    await asyncio.gather(
                        *(client.send(request) for client_id, client in self._connected_simulators.items()),
                        return_exceptions=True,
                    )
                except Exception as send_error:
                    RenderingSocket._logger.error(f"Error gathering images: {send_error}")
                    raise

            RenderingSocket._logger.debug(f"Waiting for all images of time step {time_step}")
            await self._image_cache.wait_for_images(time_step, self._connected_simulator_ids)
            RenderingSocket._logger.debug(f"Waiting for all images of time step {time_step} ... success.")
            results = self._image_cache.get(time_step)
            if self._image_receiver_socket is not None:
                RenderingSocket._logger.debug(f"Images of time step {time_step} sending to image receiver...")
                json = ImagesAtTimeStep(
                    time_step=time_step,
                    images=results,
                ).model_dump_json()
                message_size_mb = len(json) / (1024 * 1024)
                RenderingSocket._logger.debug(
                    f"Images of time step {time_step} sending to image receiver: message_size_mb = {message_size_mb} MB",
                )
                await self._image_receiver_socket.send(json)
                RenderingSocket._logger.debug(f"Images of time step {time_step} sending to image receiver... success.")
            else:
                RenderingSocket._logger.warning(
                    f"Rendering images at time step {time_step} were received, but no image receiver control server is connected => "
                    + "continue without sending.",
                )
        except Exception as e:
            RenderingSocket._logger.error(f"Error sending images at time step {time_step}: {e}")
        finally:
            end_event.set()
            current_value = self._currently_sending_processes.dec()
            if current_value == 0:
                self._no_sending_in_progress.set()

    @override
    def on_app_shutdown(self) -> None:
        self.close()
