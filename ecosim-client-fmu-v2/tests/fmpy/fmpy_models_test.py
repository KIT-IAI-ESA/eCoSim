from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List
from uuid import uuid4

import fmpy
from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave

from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import resource_path
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData

_SUB1_FMU_FILE = resource_path() / "fmu_v2" / "test_fmus" / "Sub1_Linux.fmu"
_SUB2_FMU_FILE = resource_path() / "fmu_v2" / "test_fmus" / "Sub2_Linux.fmu"


@dataclass
class FMUInput:
    value_name: str
    init_value: float
    increase_by_step: float


@skip_unless_fmpy_loads(_SUB1_FMU_FILE)
def test_sim() -> None:
    model_description = read_model_description(f"{_SUB1_FMU_FILE}")

    unzipdir = extract(_SUB1_FMU_FILE)

    if model_description.fmiVersion == "2.0":
        fmu_instance = FMU2Slave(
            guid=model_description.guid,
            unzipDirectory=unzipdir,
            modelIdentifier=model_description.coSimulation.modelIdentifier,
            instanceName="instance1",
        )
    else:
        raise RuntimeError(f"Unsupported FMI version: {model_description.fmiVersion}")

    start_time = 0.0
    fmu_instance.instantiate()
    fmu_instance.setupExperiment(startTime=start_time)
    fmu_instance.enterInitializationMode()
    fmu_instance.exitInitializationMode()

    print("")

    # step_size: 0.1
    # pos_2: 0.001
    # speed_2: 0.007
    # Time: 0.1, Outputs: {'pos_1': 0.44142016826641434, 'speed_1': -1.121094103090904}
    # Time: 0.2, Outputs: {'pos_1': 0.2891553708658837, 'speed_1': -1.8437541758129694}

    input_variables = [v for v in model_description.modelVariables if v.causality == "input"]
    input_values = {
        "pos_2": 0.3,
        "speed_2": 0.9,
    }
    # input_values = {
    #     'inputs': 99999
    # }
    input_refs = {var.name: var.valueReference for var in input_variables}
    for var_name, value in input_values.items():
        fmu_instance.setReal(
            [input_refs[var_name]],
            [value],
        )
        print(f"Set {var_name} to {value}")

    # set inputs
    for var_name, value in input_values.items():
        value_after_set = fmu_instance.getReal([input_refs[var_name]])
        print(f"After set {var_name}: {value_after_set}")

    step_size = 0.1  # Define the step size
    fmu_instance.doStep(
        currentCommunicationPoint=start_time,
        communicationStepSize=step_size,
    )

    # Get the FMU state after the first step
    time = start_time + step_size

    output_variables = [v for v in model_description.modelVariables if v.causality == "output"]
    output_values = {var.name: fmu_instance.getReal([var.valueReference])[0] for var in output_variables}

    print(f"Time: {time}, Outputs: {output_values}")

    # set inputs
    for var_name, value in input_values.items():
        value_after_set = fmu_instance.getReal([input_refs[var_name]])
        print(f"After set {var_name}: {value_after_set}")

    fmu_instance.doStep(
        time,
        communicationStepSize=step_size,
    )
    output_variables = [v for v in model_description.modelVariables if v.causality == "output"]
    output_values = {var.name: fmu_instance.getReal([var.valueReference])[0] for var in output_variables}

    print(f"Time: {time + step_size}, Outputs: {output_values}")

    # Cleanup
    fmu_instance.terminate()
    fmu_instance.freeInstance()
    shutil.rmtree(unzipdir)


@skip_unless_fmpy_loads(_SUB2_FMU_FILE)
def test_fmpy() -> None:
    print("")
    print("")

    unzip_dir = fmpy.extract(_SUB2_FMU_FILE)

    step_size = 1.0

    model_description = fmpy.read_model_description(f"{_SUB2_FMU_FILE}")
    input_variables = [v for v in model_description.modelVariables if v.causality == "input"]
    input_value_references = {var.name: var.valueReference for var in input_variables}
    output_variables = [v for v in model_description.modelVariables if v.causality == "output"]
    output_value_references = {var.name: var.valueReference for var in output_variables}

    fmu_instance = fmpy.fmi2.FMU2Slave(
        guid=model_description.guid,
        unzipDirectory=unzip_dir,
        modelIdentifier=model_description.coSimulation.modelIdentifier,
        instanceName=str(uuid4()),
    )

    fmu_instance.instantiate()
    fmu_instance.setupExperiment(startTime=0.0)
    fmu_instance.enterInitializationMode()
    fmu_instance.exitInitializationMode()

    fmu_instance.setReal(
        [input_value_references["pos1"]],
        [1.0],
    )
    fmu_instance.setReal(
        [input_value_references["speed1"]],
        [1.0],
    )

    print("=== INPUT")
    print(f"Pos1: {fmu_instance.getReal([input_value_references['pos1']])}")
    print(f"Speed1: {fmu_instance.getReal([input_value_references['speed1']])}")
    print(f"Step size: {step_size}")

    fmu_instance.doStep(
        currentCommunicationPoint=0.0,
        communicationStepSize=step_size,
    )

    print("=== RESULT")
    print(f"Pos2: {fmu_instance.getReal([output_value_references['pos2']])}")
    print(f"Speed2: {fmu_instance.getReal([output_value_references['speed2']])}")

    shutil.rmtree(unzip_dir)


@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()
def test_fmpy_houses_weather() -> None:
    _execute_fmu(
        fmu_file=HouseSimulationData.fmu_file("weather"),
        steps=12,
        step_size=60000,
        inputs=[],
        outputs=["dir_sol_irradiance", "T_out"],
    )


@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()
def test_fmpy_houses_house() -> None:
    _execute_fmu(
        fmu_file=HouseSimulationData.fmu_file("house"),
        steps=10,
        step_size=100,
        inputs=[
            FMUInput(
                value_name="T_out",
                init_value=220.0,
                increase_by_step=0.5,
            ),
            FMUInput(
                value_name="ventilation_pressure_control_signal",
                init_value=1.0,
                increase_by_step=1.5,
            ),
            FMUInput(
                value_name="heating_heatExchanger_control_signal",
                init_value=1.2,
                increase_by_step=1.7,
            ),
            FMUInput(
                value_name="vetnilation_valve_control_signal",
                init_value=1.5,
                increase_by_step=1.9,
            ),
            FMUInput(
                value_name="dir_sol_iradiance",
                init_value=1.7,
                increase_by_step=0.8,
            ),
        ],
        outputs=["room_temperature"],
    )


@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()
def test_fmpy_houses_heating() -> None:
    _execute_fmu(
        fmu_file=HouseSimulationData.fmu_file("heating"),
        steps=10,
        step_size=60,
        inputs=[
            FMUInput(
                value_name="T_room",
                init_value=220.0,
                increase_by_step=20.0,
            ),
        ],
        outputs=["heating_control_signal"],
    )


@HouseSimulationData.skip_unless_fmpy_loads_the_fmus()
def test_fmpy_houses_ventilation() -> None:
    _execute_fmu(
        fmu_file=HouseSimulationData.fmu_file("ventilation"),
        steps=10,
        step_size=60,
        inputs=[
            FMUInput(
                value_name="T_room",
                init_value=220.0,
                increase_by_step=10.0,
            ),
        ],
        outputs=["ventilation_pressure_control_signal", "ventilation_valve_control_signal"],
    )


def _execute_fmu(
    fmu_file: Path,
    steps: int,
    step_size: float,
    inputs: List[FMUInput],
    outputs: List[str],
) -> None:
    print("")
    print("")
    unzip_dir = fmpy.extract(fmu_file)
    model_description = fmpy.read_model_description(fmu_file)

    fmu_instance = fmpy.fmi2.FMU2Slave(
        guid=model_description.guid,
        unzipDirectory=unzip_dir,
        modelIdentifier=model_description.coSimulation.modelIdentifier,
        instanceName=str(uuid4()),
    )

    fmu_instance.instantiate()
    fmu_instance.setupExperiment(startTime=0.0)
    fmu_instance.enterInitializationMode()
    fmu_instance.exitInitializationMode()

    value_references = {var.name: var.valueReference for var in model_description.modelVariables}

    print("=== INPUT")
    print(f"Steps: {steps}")
    print(f"Step size: {step_size}")
    for fmu_input in inputs:
        fmu_instance.setReal([value_references[fmu_input.value_name]], [fmu_input.init_value])
        print(
            f"Inputs: {fmu_instance.getReal([value_references[fmu_input.value_name]])} | Increase by: {fmu_input.increase_by_step}",
        )
    print("")
    print("")

    for current_step in range(steps):
        for fmu_input in inputs:
            fmu_instance.setReal(
                [value_references[fmu_input.value_name]],
                [fmu_input.init_value + (current_step * fmu_input.increase_by_step)],
            )
        fmu_instance.doStep(
            currentCommunicationPoint=current_step * step_size,
            communicationStepSize=step_size,
        )
        print(f"=== RESULT: Step {current_step}")
        for output in outputs:
            print(f"{output}: {fmu_instance.getReal([value_references[output]])}")
        print("")
        print("")

    fmu_instance.freeInstance()
    shutil.rmtree(unzip_dir)
