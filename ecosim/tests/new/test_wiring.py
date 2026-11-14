from ecosim.new.interface_address import InterfaceAddress
from ecosim.new.wiring import Connection, OpenInput, Wiring

from tests.new.simulation_models import create_interface, create_model


def test_an_input_is_connected_to_the_one_output_of_another_model_with_its_name() -> None:
    wiring = Wiring.of_models(models=[create_model(name="house", inputs=["T_out"]), create_model(name="weather", outputs=["T_out"])])

    assert wiring.connections == (
        Connection(input=InterfaceAddress(model="house", name="T_out"), output=InterfaceAddress(model="weather", name="T_out")),
    )
    assert wiring.open_inputs == ()


def test_a_dot_and_an_underscore_count_as_the_same_in_names() -> None:
    wiring = Wiring.of_models(
        models=[create_model(name="house", inputs=["weatherBus_TDryBul"]), create_model(name="weather", outputs=["weatherBus.TDryBul"])],
    )

    assert [connection.output for connection in wiring.connections] == [InterfaceAddress(model="weather", name="weatherBus.TDryBul")]


def test_an_input_with_two_matching_outputs_stays_open_and_names_both() -> None:
    models = [
        create_model(name="house", inputs=["T_out"]),
        create_model(name="weather", outputs=["T_out"]),
        create_model(name="sensor", outputs=["T.out"]),
    ]

    wiring = Wiring.of_models(models=models)

    assert wiring.connections == ()
    assert wiring.open_inputs == (
        OpenInput(
            input=InterfaceAddress(model="house", name="T_out"),
            outputs_with_its_name=(InterfaceAddress(model="weather", name="T_out"), InterfaceAddress(model="sensor", name="T.out")),
        ),
    )


def test_an_input_is_never_matched_to_an_output_of_its_own_model() -> None:
    wiring = Wiring.of_models(models=[create_model(name="controller", inputs=["signal"], outputs=["signal"])])

    assert wiring.connections == ()
    assert wiring.open_inputs == (OpenInput(input=InterfaceAddress(model="controller", name="signal"), outputs_with_its_name=()),)


def test_an_array_output_is_not_matched_to_an_input_of_another_size() -> None:
    models = [create_model(name="controller", inputs=["u"]), create_model(name="plant", outputs=[create_interface(name="u", shape=(3,))])]

    wiring = Wiring.of_models(models=models)

    assert wiring.connections == ()
    assert wiring.open_inputs[0].outputs_with_its_name == (InterfaceAddress(model="plant", name="u"),)


def test_an_array_output_is_matched_to_an_input_of_another_shape_that_takes_as_many_values() -> None:
    models = [
        create_model(name="plant", inputs=[create_interface(name="u", shape=(6,))]),
        create_model(name="controller", outputs=[create_interface(name="u", shape=(2, 3))]),
    ]

    wiring = Wiring.of_models(models=models)

    assert [connection.output for connection in wiring.connections] == [InterfaceAddress(model="controller", name="u")]
