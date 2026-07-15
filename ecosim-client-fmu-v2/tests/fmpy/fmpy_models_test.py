from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass
from typing import List
from uuid import uuid4

import fmpy
import pytest
from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave

from tests.tech.resource_utils import resource_path


@dataclass
class FMUInput:
    value_name: str
    init_value: float
    increase_by_step: float


def get_os_name_lower_case() -> str:
    return str.lower(platform.system())


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on Windows")
def test_sim() -> None:
    fmu_file = os.path.join(resource_path(), "test_fmus", "Sub1_Linux.fmu")
    # fmu_file = 'CoupledClutches.fmu'
    # download_test_file('2.0', 'CoSimulation', 'MapleSim', '2016.2', 'CoupledClutches', fmu_file)
    model_description = read_model_description(f"{fmu_file}")

    unzipdir = extract(fmu_file)

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


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on Windows")
def test_fmpy() -> None:
    print("")
    print("")

    fmu_file = os.path.join(resource_path(), "test_fmus", "Sub2_Linux.fmu")
    unzip_dir = fmpy.extract(fmu_file)

    step_size = 1.0

    model_description = fmpy.read_model_description(f"{fmu_file}")
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


@pytest.mark.skip(reason="manual test")
def test_fmpy_coupled_clutches() -> None:
    print("")
    print("")

    fmu_file = os.path.join(resource_path(), "test_fmus", "CoupledClutches.fmu")
    unzip_dir = fmpy.extract(fmu_file)

    step_size = 100000.0

    model_description = fmpy.read_model_description(f"{fmu_file}")
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
        [input_value_references["inputs"]],
        [1.0],
    )

    print("=== INPUT")
    print(f"Inputs: {fmu_instance.getReal([input_value_references['inputs']])}")
    print(f"Step size: {step_size}")

    fmu_instance.doStep(
        currentCommunicationPoint=0.0,
        communicationStepSize=step_size,
    )

    print("=== RESULT")
    print(f"Outputs[1]: {fmu_instance.getReal([output_value_references['outputs[1]']])}")
    print(f"Outputs[2]: {fmu_instance.getReal([output_value_references['outputs[2]']])}")
    print(f"Outputs[3]: {fmu_instance.getReal([output_value_references['outputs[3]']])}")
    print(f"Outputs[4]: {fmu_instance.getReal([output_value_references['outputs[4]']])}")

    shutil.rmtree(unzip_dir)


def test_fmpy_houses_weather() -> None:
    _execute_fmu(
        fmu_file=os.path.join("models", "house", get_os_name_lower_case(), "weather.fmu"),
        steps=12,
        step_size=60000,
        inputs=[],
        outputs=["dir_sol_irradiance", "T_out"],
    )


def test_fmpy_houses_house() -> None:
    _execute_fmu(
        fmu_file=os.path.join("models", "house", get_os_name_lower_case(), "house.fmu"),
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


def test_fmpy_houses_heating() -> None:
    _execute_fmu(
        fmu_file=os.path.join("models", "house", get_os_name_lower_case(), "heating.fmu"),
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


def test_fmpy_houses_ventilation() -> None:
    _execute_fmu(
        fmu_file=os.path.join("models", "house", get_os_name_lower_case(), "ventilation.fmu"),
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
    fmu_file: str,
    steps: int,
    step_size: float,
    inputs: List[FMUInput],
    outputs: List[str],
) -> None:
    print("")
    print("")
    full_path = os.path.join(resource_path(), fmu_file)
    unzip_dir = fmpy.extract(full_path)
    model_description = fmpy.read_model_description(full_path)

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
