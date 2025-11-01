from ecosim_client_fmu_v3.fmu3_config import FMU3Config
from ecosim_client_fmu_v3.fmu3_simulator import FMU3Simulator
from ecosim_common.client.config.execution_config import ExecutionConfig
from tests.tech.resource_utils import resource_path


def test_simulator() -> None:
    step_size_in_seconds = 1
    simulator = FMU3Simulator.of(
        simulator_name='test_simulator',
        fmu_config=FMU3Config(
            fmu_file=resource_path() / 'test_fmus/StateSpace.fmu',
        ),
        execution_config=ExecutionConfig(
            step_size_in_ms=step_size_in_seconds * 1000,
        ),
    )

    simulator.initialize()

    simulator.do_step(
        input_values={
            'u': [111, 222, 333],
        },
        step_size_in_seconds=step_size_in_seconds,
    )

    y = simulator.get_output_float_matrix("y", 3)

    assert len(y) == 3
    assert y[0] == 301.57855647818417
    assert y[1] == 603.1571129563683
    assert y[2] == 904.7356694345515

    simulator.do_step(
        input_values={
            'u': [222, 444, 666],
        },
        step_size_in_seconds=step_size_in_seconds,
    )

    y = simulator.get_output_float_matrix("y")

    assert len(y) == 3
    assert y[0] == 1120.9445540229174
    assert y[1] == 2241.8891080458347
    assert y[2] == 3362.8336620687433

    simulator.clear()
