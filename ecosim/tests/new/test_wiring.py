import pytest
from ecosim.new.interface_address import InterfaceAddress
from ecosim.new.wiring import Connection, OpenInput, Wiring

from tests.new.simulation_models import create_interface, create_model


def test_an_input_is_connected_to_the_one_output_of_another_model_with_its_name() -> None:
    wiring = Wiring.of_models(
        models=[create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])],
        given_connections=[],
    )

    assert wiring.connections == (
        Connection(input=InterfaceAddress(model="house", name="T_out"), output=InterfaceAddress(model="weather", name="T_out"), matched_by_name=True),
    )
    assert wiring.open_inputs == ()


def test_a_dot_and_an_underscore_count_as_the_same_in_names() -> None:
    wiring = Wiring.of_models(
        models=[create_model(name="house", inputs=["weatherBus_TDryBul"]), create_model(name="weather", outputs=["weatherBus.TDryBul"])],
        given_connections=[],
    )

    assert [connection.output for connection in wiring.connections] == [InterfaceAddress(model="weather", name="weatherBus.TDryBul")]


def test_an_input_with_two_matching_outputs_stays_open_and_names_both() -> None:
    models = [
        create_model(name="house", inputs=["T_out"]),
        create_model(name="weather", outputs=["T_out"]),
        create_model(name="sensor", outputs=["T.out"]),
    ]

    wiring = Wiring.of_models(models=models, given_connections=[])

    assert wiring.connections == ()
    assert wiring.open_inputs == (
        OpenInput(
            input=InterfaceAddress(model="house", name="T_out"),
            outputs_with_its_name=(InterfaceAddress(model="weather", name="T_out"), InterfaceAddress(model="sensor", name="T.out")),
        ),
    )


def test_an_input_is_never_matched_to_an_output_of_its_own_model() -> None:
    wiring = Wiring.of_models(models=[create_model(name="controller", inputs=["signal"], outputs=["signal"])], given_connections=[])

    assert wiring.connections == ()
    assert wiring.open_inputs == (OpenInput(input=InterfaceAddress(model="controller", name="signal"), outputs_with_its_name=()),)


def test_an_array_output_is_not_matched_to_an_input_of_another_size() -> None:
    models = [create_model(name="controller", inputs=["u"]), create_model(name="plant", outputs=[create_interface(name="u", shape=(3,))])]

    wiring = Wiring.of_models(models=models, given_connections=[])

    assert wiring.connections == ()
    assert wiring.open_inputs[0].outputs_with_its_name == (InterfaceAddress(model="plant", name="u"),)


def test_an_array_output_is_matched_to_an_input_of_another_shape_that_takes_as_many_values() -> None:
    models = [
        create_model(name="plant", inputs=[create_interface(name="u", shape=(6,))]),
        create_model(name="controller", outputs=[create_interface(name="u", shape=(2, 3))]),
    ]

    wiring = Wiring.of_models(models=models, given_connections=[])

    assert [connection.output for connection in wiring.connections] == [InterfaceAddress(model="controller", name="u")]


def test_a_given_connection_replaces_the_name_match() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out", "T_dry"])]

    wiring = Wiring.of_models(models=models, given_connections=["house.T_out=weather.T_dry"])

    assert wiring.connections == (
        Connection(
            input=InterfaceAddress(model="house", name="T_out"),
            output=InterfaceAddress(model="weather", name="T_dry"),
            matched_by_name=False,
        ),
    )


def test_a_given_connection_to_a_missing_input_names_the_close_one() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])]

    with pytest.raises(ValueError) as error:
        Wiring.of_models(models=models, given_connections=["house.T_ou=weather.T_out"])

    assert str(error.value) == "--connect house.T_ou=weather.T_out: house has no input T_ou. Did you mean T_out?"


def test_a_given_connection_that_starts_with_the_output_says_to_write_the_input_first() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])]

    with pytest.raises(ValueError) as error:
        Wiring.of_models(models=models, given_connections=["weather.T_out=house.T_out"])

    assert str(error.value) == "--connect weather.T_out=house.T_out: weather.T_out is not an input. Write the input first, then '=' and the output."


def test_a_second_given_connection_of_one_input_is_refused() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out", "T_dry"])]

    with pytest.raises(ValueError, match="house.T_out is connected to weather.T_out already. An input takes one output."):
        Wiring.of_models(models=models, given_connections=["house.T_out=weather.T_out", "house.T_out=weather.T_dry"])


def test_a_given_connection_to_a_model_that_does_not_exist_names_the_models() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])]

    with pytest.raises(ValueError) as error:
        Wiring.of_models(models=models, given_connections=["house.T_out=wxyz.T_out"])

    assert str(error.value) == "--connect house.T_out=wxyz.T_out: there is no model wxyz. The models are house and weather."


def test_a_given_connection_to_an_output_with_another_number_of_values_is_refused() -> None:
    models = [create_model(name="plant", inputs=[create_interface(name="u", shape=(3,))]), create_model(name="controller", outputs=["y"])]

    with pytest.raises(ValueError) as error:
        Wiring.of_models(models=models, given_connections=["plant.u=controller.y"])

    assert str(error.value) == "--connect plant.u=controller.y: controller.y holds 1 value, but plant.u takes 3."
