import asyncio
from pathlib import Path
from unittest.mock import Mock

import websockets

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.renderer.pre_rendered_images_service import PreRenderedImageService, \
    PreRenderedImageServiceConfig
from ecosim_common.client.renderer.rendering_socket_client import RenderingSocketClient
from ecosim_common.config.client_id import ClientID
from ecosim_common.simulation.renderer.rendering_messages import RenderingImageMessage, RawRenderingMessageHandler, \
    RenderingMessageType, ImagesAtTimeStep
from ecosim_server.simulation.rendering.rendering_socket import RenderingSocket


def test_local_test():
    server_socket = RenderingSocket(
        host='localhost',
        port=3336,
    )
    server_socket.start().wait()

    mock_config = Mock(spec=ClientConfig)
    mock_config.client_id.return_value = ClientID(model_name="Model", simulator_name="Simulator")
    mock_config.config_path = "non-existing-dir"

    test_dir = Path(__file__).parent.parent
    resources_dir = test_dir / "resources"
    renderer_service = PreRenderedImageService(
        PreRenderedImageServiceConfig(
            image_dir=f"{resources_dir}/rendered_images",
        )
    )
    client = RenderingSocketClient(
        uri="ws://localhost:3336",
        client_config=mock_config,
        renderer_service=renderer_service,
    )
    client.start().wait()

    loop = asyncio.get_event_loop()
    image_receiver_connection = loop.run_until_complete(websockets.connect("ws://localhost:3336", additional_headers={
        'client_id': 'sim_control'
    }))

    # test trigger by web socket message
    loop.run_until_complete(
        image_receiver_connection.send(RenderingImageMessage(
            time_step=100,
        ).model_dump_json())
    )
    message = RawRenderingMessageHandler(loop.run_until_complete(image_receiver_connection.recv()))
    assert message.message_type() == RenderingMessageType.IMAGES_AT_TIME_STEP
    message = message.cast(ImagesAtTimeStep)
    assert message.time_step == 100

    loop.run_until_complete(
        image_receiver_connection.send(RenderingImageMessage(
            time_step=200,
        ).model_dump_json())
    )
    message = RawRenderingMessageHandler(loop.run_until_complete(image_receiver_connection.recv()))
    assert message.message_type() == RenderingMessageType.IMAGES_AT_TIME_STEP
    message = message.cast(ImagesAtTimeStep)
    assert message.time_step == 200

    # test trigger by calling the method directly
    server_socket.request_and_send_images(100).wait(timeout=8)
    message = RawRenderingMessageHandler(loop.run_until_complete(image_receiver_connection.recv()))
    assert message.message_type() == RenderingMessageType.IMAGES_AT_TIME_STEP
    message = message.cast(ImagesAtTimeStep)
    assert message.time_step == 100

    server_socket.request_and_send_images(200).wait(timeout=4)
    message = RawRenderingMessageHandler(loop.run_until_complete(image_receiver_connection.recv()))
    assert message.message_type() == RenderingMessageType.IMAGES_AT_TIME_STEP
    message = message.cast(ImagesAtTimeStep)
    assert message.time_step == 200
