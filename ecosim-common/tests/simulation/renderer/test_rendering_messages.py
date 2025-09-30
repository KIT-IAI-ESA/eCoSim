from ecosim_common.simulation.renderer.rendering_messages import ImagesAtTimeStep, RenderingMessageType


def test_parse_message_images_at_time_step__empty_images() -> None:
    message = ImagesAtTimeStep.from_json({
        "message_type": RenderingMessageType.IMAGES_AT_TIME_STEP.value,
        "time_step": 123,
        "images": {}
    })
    assert message.message_type == RenderingMessageType.IMAGES_AT_TIME_STEP
    assert message.time_step == 123
    assert len(message.images) == 0


def test_parse_message_images_at_time_step__with_image() -> None:
    message = ImagesAtTimeStep.from_json({
        "message_type": RenderingMessageType.IMAGES_AT_TIME_STEP.value,
        "time_step": 123,
        "images": {
            "module1": {
                "message_type": RenderingMessageType.RENDERING_IMAGE_REPLY.value,
                "time_step": 123,
                "base64": "9999",
            }
        }
    })
    assert message.message_type == RenderingMessageType.IMAGES_AT_TIME_STEP
    assert message.time_step == 123
    assert len(message.images) == 1
    assert message.images["module1"].base64 == "9999"
