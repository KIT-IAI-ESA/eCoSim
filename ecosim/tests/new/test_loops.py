import pytest
from ecosim.new.delayed_input import DelayedInput
from ecosim.new.loops import breaking_connections, ensure_no_loop, loops_of
from ecosim.new.wiring import Wiring

from tests.new.simulation_models import create_interface, create_model

HOUSE_AND_CONTROLLERS = [
    create_model(name="house", inputs=["heating_signal", "ventilation_signal"], outputs=["room_temperature"]),
    # not 0, so the test tells the start value of the FMU from a fixed one
    create_model(name="heating", inputs=[create_interface(name="room_temperature", start="21.5")], outputs=["heating_signal"]),
    create_model(name="ventilation", inputs=["room_temperature"], outputs=["ventilation_signal"]),
]


def _wiring_of_the_house_and_its_controllers() -> Wiring:
    return Wiring.of_models(models=HOUSE_AND_CONTROLLERS, given_connections=[])


def test_models_that_feed_each_other_form_one_loop() -> None:
    loops = loops_of(connections=_wiring_of_the_house_and_its_controllers().connections, delayed=[])

    assert [sorted({connection.input.model for connection in loop}) for loop in loops] == [["heating", "house", "ventilation"]]


def test_the_suggested_delays_are_the_inputs_fed_by_the_model_every_loop_passes() -> None:
    loop = loops_of(connections=_wiring_of_the_house_and_its_controllers().connections, delayed=[])[0]

    assert sorted(str(connection.input) for connection in breaking_connections(loop=loop)) == [
        "heating.room_temperature",
        "ventilation.room_temperature",
    ]


def test_a_loop_stops_with_its_connections_and_the_delays_that_break_it() -> None:
    with pytest.raises(ValueError) as error:
        ensure_no_loop(connections=_wiring_of_the_house_and_its_controllers().connections, delayed=[])

    assert str(error.value).splitlines() == [
        "heating, house and ventilation feed each other, so the server could start none of them:",
        "  house.heating_signal  <-  heating.heating_signal",
        "  house.ventilation_signal  <-  ventilation.ventilation_signal",
        "  heating.room_temperature  <-  house.room_temperature",
        "  ventilation.room_temperature  <-  house.room_temperature",
        "Give inputs the value of the step before to break the loop, for example:",
        "  --logical-delay heating.room_temperature --logical-delay ventilation.room_temperature",
    ]


def test_delaying_the_suggested_inputs_leaves_no_loop() -> None:
    wiring = _wiring_of_the_house_and_its_controllers()
    texts = ["heating.room_temperature", "ventilation.room_temperature"]

    delayed = DelayedInput.of_texts(texts=texts, models=HOUSE_AND_CONTROLLERS, wiring=wiring)

    assert loops_of(connections=wiring.connections, delayed=delayed) == []


def test_a_delayed_input_starts_with_the_start_value_of_its_fmu_or_the_given_one() -> None:
    texts = ["heating.room_temperature", "ventilation.room_temperature=293.15"]

    delayed = DelayedInput.of_texts(texts=texts, models=HOUSE_AND_CONTROLLERS, wiring=_wiring_of_the_house_and_its_controllers())

    assert [delayed_input.start_value for delayed_input in delayed] == [21.5, 293.15]


def test_a_delayed_array_input_takes_one_start_value_for_each_of_its_values() -> None:
    models = [
        create_model(name="plant", inputs=[create_interface(name="u", shape=(3,))]),
        create_model(name="controller", outputs=[create_interface(name="u", shape=(3,))]),
    ]
    wiring = Wiring.of_models(models=models, given_connections=[])

    assert DelayedInput.of_texts(texts=["plant.u=1,2,3"], models=models, wiring=wiring)[0].start_value == [1.0, 2.0, 3.0]
    with pytest.raises(ValueError, match="the start value must be 3 numbers separated by commas, not '1,2'"):
        DelayedInput.of_texts(texts=["plant.u=1,2"], models=models, wiring=wiring)


def test_an_input_that_is_not_connected_cannot_be_delayed() -> None:
    models = [create_model(name="heating", inputs=["T_room"])]

    with pytest.raises(ValueError) as error:
        DelayedInput.of_texts(texts=["heating.T_room"], models=models, wiring=Wiring.of_models(models=models, given_connections=[]))

    assert str(error.value) == "--logical-delay heating.T_room: heating.T_room is not connected, so there is nothing to delay."


def test_a_connection_to_an_output_of_its_own_model_needs_a_logical_delay() -> None:
    models = [create_model(name="controller", inputs=["last_signal"], outputs=["signal"])]
    wiring = Wiring.of_models(models=models, given_connections=["controller.last_signal=controller.signal"])

    with pytest.raises(ValueError, match="feeds controller its own output, which needs --logical-delay controller.last_signal$"):
        DelayedInput.of_texts(texts=[], models=models, wiring=wiring)
    assert [str(delayed_input.input) for delayed_input in DelayedInput.of_texts(texts=["controller.last_signal"], models=models, wiring=wiring)] == [
        "controller.last_signal",
    ]


def test_a_logical_delay_on_an_output_says_that_it_goes_on_an_input() -> None:
    with pytest.raises(ValueError) as error:
        DelayedInput.of_texts(texts=["house.room_temperature"], models=HOUSE_AND_CONTROLLERS, wiring=_wiring_of_the_house_and_its_controllers())

    assert str(error.value) == (
        "--logical-delay house.room_temperature: house.room_temperature is not an input. A logical delay goes on an input, like heating.T_room"
    )


def test_a_second_logical_delay_of_one_input_is_refused() -> None:
    texts = ["heating.room_temperature", "heating.room_temperature=20"]

    with pytest.raises(ValueError) as error:
        DelayedInput.of_texts(texts=texts, models=HOUSE_AND_CONTROLLERS, wiring=_wiring_of_the_house_and_its_controllers())

    assert str(error.value) == "--logical-delay heating.room_temperature=20: heating.room_temperature has a logical delay already."


@pytest.mark.parametrize("start", ["inf", "nan", "warm"])
def test_a_start_value_that_is_not_a_number_is_refused(start: str) -> None:
    wiring = _wiring_of_the_house_and_its_controllers()

    with pytest.raises(ValueError) as error:
        DelayedInput.of_texts(texts=[f"heating.room_temperature={start}"], models=HOUSE_AND_CONTROLLERS, wiring=wiring)

    assert str(error.value) == f"--logical-delay heating.room_temperature={start}: the start value must be a number, not '{start}'."
