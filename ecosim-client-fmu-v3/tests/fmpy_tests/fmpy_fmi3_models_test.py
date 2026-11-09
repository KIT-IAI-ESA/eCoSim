from __future__ import annotations

import shutil

from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from fmpy import read_model_description, extract
from fmpy.fmi3 import FMU3Slave

from tests.tech.resource_utils import resource_path

_FEEDTHROUGH_FMU_FILE = resource_path() / "test_fmus" / "Feedthrough.fmu"
_STATE_SPACE_FMU_FILE = resource_path() / "test_fmus" / "StateSpace.fmu"


# This is only a test to play around with the FMI3 implementation of fmpy
@skip_unless_fmpy_loads(_FEEDTHROUGH_FMU_FILE)
def test_feedthrough() -> None:
    model_description = read_model_description(f"{_FEEDTHROUGH_FMU_FILE}")

    unzipdir = extract(_FEEDTHROUGH_FMU_FILE)

    if model_description.fmiVersion == "3.0":
        fmu_instance = FMU3Slave(
            guid=model_description.guid,
            unzipDirectory=unzipdir,
            modelIdentifier=model_description.coSimulation.modelIdentifier,
            instanceName="instance1",
        )
    else:
        raise RuntimeError(f"Unsupported FMI version: {model_description.fmiVersion}")

    start_time = 0.0
    fmu_instance.instantiate()
    fmu_instance.enterInitializationMode(startTime=start_time)
    fmu_instance.exitInitializationMode()

    print("")
    print(f"{model_description}")

    input_variables = [v for v in model_description.modelVariables if v.causality == "input"]
    float64_continuous_input_name = "Float64_continuous_input"
    float64_discrete_input_name = "Float64_discrete_input"
    boolean_input_name = "Boolean_input"
    string_input_name = "String_input"

    input_refs = {var.name: var.valueReference for var in input_variables}
    print("")
    print(f"{input_refs}")

    # set inputs
    fmu_instance.setFloat64([input_refs[float64_continuous_input_name]], [222.211])
    fmu_instance.setFloat64([input_refs[float64_discrete_input_name]], [333.345])
    fmu_instance.setBoolean([input_refs[boolean_input_name]], [True])
    fmu_instance.setString([input_refs[string_input_name]], ["eCoSim rocks!"])

    input_values = {
        "float_discrete": fmu_instance.getFloat64([input_refs[float64_discrete_input_name]]),
        "float_continuous": fmu_instance.getFloat64([input_refs[float64_continuous_input_name]]),
        "boolean": fmu_instance.getBoolean([input_refs[boolean_input_name]]),
        "string": fmu_instance.getString([input_refs[string_input_name]]),
    }
    print(f"After set (input): {input_values}")
    output_values = {
        "float_discrete": fmu_instance.getFloat64([10]),
        "float_continuous": fmu_instance.getFloat64([8]),
        "boolean": fmu_instance.getBoolean([28]),
        "string": fmu_instance.getString([30]),
    }
    print(f"After set (output): {output_values}")

    step_size = 10  # Define the step size
    fmu_instance.doStep(
        currentCommunicationPoint=start_time,
        communicationStepSize=step_size,
    )

    # Get the FMU state after the first step
    time = start_time + step_size

    output_values = {
        "float_discrete": fmu_instance.getFloat64([10]),
        "float_continuous": fmu_instance.getFloat64([8]),
        "boolean": fmu_instance.getBoolean([28]),
        "string": fmu_instance.getString([30]),
    }
    print(f"Time: {time}, Outputs: {output_values}")

    # Cleanup
    fmu_instance.terminate()
    fmu_instance.freeInstance()
    shutil.rmtree(unzipdir)


# This is only a test to play around with the FMI3 implementation of fmpy
@skip_unless_fmpy_loads(_STATE_SPACE_FMU_FILE)
def test_state_space() -> None:
    model_description = read_model_description(f"{_STATE_SPACE_FMU_FILE}")

    unzipdir = extract(_STATE_SPACE_FMU_FILE)

    if model_description.fmiVersion == "3.0":
        fmu_instance = FMU3Slave(
            guid=model_description.guid,
            unzipDirectory=unzipdir,
            modelIdentifier=model_description.coSimulation.modelIdentifier,
            instanceName="instance1",
        )
    else:
        raise RuntimeError(f"Unsupported FMI version: {model_description.fmiVersion}")

    start_time = 0.0
    fmu_instance.instantiate()
    fmu_instance.enterInitializationMode(startTime=start_time)
    fmu_instance.exitInitializationMode()

    print("")
    print(f"{model_description}")

    # Simulation parameters
    time = 0.0
    stop_time = 3.0
    step_size = 1.0

    # Storage for results
    times = []

    # Simulation loop
    while time < stop_time:
        # Set input values at current time
        # Calculate your desired input values
        u_values = [
            111 * (time + 1),  # u[1]
            222 * (time + 1),  # u[2]
            333 * (time + 1),  # u[3]
        ]

        # Set the input vector u (value reference 9)
        # For vector variables, you set all elements at once
        fmu_instance.setFloat64([9], u_values)

        # Take a step
        fmu_instance.doStep(time, step_size, True)

        # Get outputs
        y_values = fmu_instance.getFloat64([10], 3)  # Get 3 output values
        x_values = fmu_instance.getFloat64([11], 3)  # Get 3 state values

        # Store results
        times.append(time)

        outputs = []
        outputs.append(
            {
                "y": y_values.copy(),
                "x": x_values.copy(),
                "u": u_values.copy(),
            },
        )

        # Advance time
        time += step_size
        print(f"Time: {time}, Outputs: {outputs}")

    # Cleanup
    fmu_instance.terminate()
    fmu_instance.freeInstance()
    shutil.rmtree(unzipdir)
