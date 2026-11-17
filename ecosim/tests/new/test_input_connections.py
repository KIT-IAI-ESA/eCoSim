import pytest
from ecosim.new.input_connections import Connection, InputConnections, UnconnectedInput
from ecosim.new.simulation_model_interface_id import SimulationModelInterfaceId

from tests.new.simulation_models import create_interface, create_model


def test_an_input_is_connected_to_the_one_output_of_another_model_with_its_name() -> None:
    input_connections = InputConnections.of_models(
        models=[create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])],
        given_connections=[],
    )

    assert input_connections.connections == (
        Connection(
            input=SimulationModelInterfaceId(model="house", name="T_out"),
            output=SimulationModelInterfaceId(model="weather", name="T_out"),
            matched_by_name=True,
        ),
    )
    assert input_connections.unconnected_inputs == ()


def test_a_dot_and_an_underscore_count_as_the_same_in_names() -> None:
    input_connections = InputConnections.of_models(
        models=[create_model(name="house", inputs=["weatherBus_TDryBul"]), create_model(name="weather", outputs=["weatherBus.TDryBul"])],
        given_connections=[],
    )

    assert [connection.output for connection in input_connections.connections] == [
        SimulationModelInterfaceId(model="weather", name="weatherBus.TDryBul"),
    ]


def test_an_input_with_two_matching_outputs_stays_unconnected_and_lists_both() -> None:
    models = [
        create_model(name="house", inputs=["T_out"]),
        create_model(name="weather", outputs=["T_out"]),
        create_model(name="sensor", outputs=["T.out"]),
    ]

    input_connections = InputConnections.of_models(models=models, given_connections=[])

    assert input_connections.connections == ()
    assert input_connections.unconnected_inputs == (
        UnconnectedInput(
            input=SimulationModelInterfaceId(model="house", name="T_out"),
            outputs_with_its_name=(
                SimulationModelInterfaceId(model="weather", name="T_out"),
                SimulationModelInterfaceId(model="sensor", name="T.out"),
            ),
        ),
    )


def test_an_input_is_never_matched_to_an_output_of_its_own_model() -> None:
    input_connections = InputConnections.of_models(
        models=[create_model(name="controller", inputs=["signal"], outputs=["signal"])],
        given_connections=[],
    )

    assert input_connections.connections == ()
    assert input_connections.unconnected_inputs == (
        UnconnectedInput(input=SimulationModelInterfaceId(model="controller", name="signal"), outputs_with_its_name=()),
    )


def test_an_array_output_is_not_matched_to_an_input_of_another_size() -> None:
    models = [create_model(name="controller", inputs=["u"]), create_model(name="plant", outputs=[create_interface(name="u", shape=(3,))])]

    input_connections = InputConnections.of_models(models=models, given_connections=[])

    assert input_connections.connections == ()
    assert input_connections.unconnected_inputs[0].outputs_with_its_name == (SimulationModelInterfaceId(model="plant", name="u"),)


def test_an_array_output_is_matched_to_an_input_of_another_shape_and_the_same_size() -> None:
    models = [
        create_model(name="plant", inputs=[create_interface(name="u", shape=(6,))]),
        create_model(name="controller", outputs=[create_interface(name="u", shape=(2, 3))]),
    ]

    input_connections = InputConnections.of_models(models=models, given_connections=[])

    assert [connection.output for connection in input_connections.connections] == [SimulationModelInterfaceId(model="controller", name="u")]


def test_a_given_connection_replaces_the_name_match() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out", "T_dry"])]

    input_connections = InputConnections.of_models(models=models, given_connections=["house.T_out=weather.T_dry"])

    assert input_connections.connections == (
        Connection(
            input=SimulationModelInterfaceId(model="house", name="T_out"),
            output=SimulationModelInterfaceId(model="weather", name="T_dry"),
            matched_by_name=False,
        ),
    )


def test_a_given_connection_to_a_missing_input_suggests_the_close_one() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])]

    with pytest.raises(ValueError) as error:
        InputConnections.of_models(models=models, given_connections=["house.T_ou=weather.T_out"])

    assert str(error.value) == "--connect house.T_ou=weather.T_out: house has no input T_ou. Did you mean T_out?"


def test_a_given_connection_that_starts_with_the_output_asks_for_the_input_first() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])]

    with pytest.raises(ValueError) as error:
        InputConnections.of_models(models=models, given_connections=["weather.T_out=house.T_out"])

    assert str(error.value) == "--connect weather.T_out=house.T_out: weather.T_out is not an input. Write the input first, then '=' and the output."


def test_a_second_given_connection_of_one_input_is_rejected() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out", "T_dry"])]

    with pytest.raises(ValueError, match="house.T_out is connected to weather.T_out already."):
        InputConnections.of_models(models=models, given_connections=["house.T_out=weather.T_out", "house.T_out=weather.T_dry"])


def test_a_given_connection_to_a_model_that_does_not_exist_lists_the_models() -> None:
    models = [create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])]

    with pytest.raises(ValueError) as error:
        InputConnections.of_models(models=models, given_connections=["house.T_out=wxyz.T_out"])

    assert str(error.value) == "--connect house.T_out=wxyz.T_out: there is no model wxyz. The models are house and weather."


def test_a_given_connection_to_an_output_with_another_number_of_values_is_rejected() -> None:
    models = [create_model(name="plant", inputs=[create_interface(name="u", shape=(3,))]), create_model(name="controller", outputs=["y"])]

    with pytest.raises(ValueError) as error:
        InputConnections.of_models(models=models, given_connections=["plant.u=controller.y"])

    assert str(error.value) == "--connect plant.u=controller.y: controller.y has 1 value, but plant.u takes 3."
