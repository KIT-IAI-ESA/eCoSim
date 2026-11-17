from __future__ import annotations

import inspect
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.tech.one_line_errors import one_line_message

from ecosim_client_python.model_import import import_model_factory
from ecosim_client_python.python_config import PythonConfig


@dataclass(kw_only=True)
class PythonModel:
    model_reference: str
    _model: Any
    _step_time_parameters: frozenset[str]
    _inputs: dict[str, InterfaceValue] = field(default_factory=dict)
    _outputs: Mapping[str, Any] = field(default_factory=dict)
    _outputs_returned_by: str = field(default="initialize")

    @staticmethod
    def of_config(config: PythonConfig) -> PythonModel:
        model_factory = import_model_factory(config=config)
        try:
            model = model_factory()
        except Exception as error:
            raise RuntimeError(f"The model {config.model_reference} failed while it was created: {one_line_message(error=error)}") from error
        return PythonModel.of_object(model=model, model_reference=config.model_reference)

    @staticmethod
    def of_object(model: Any, model_reference: str) -> PythonModel:
        missing_methods = [f"{name}()" for name in ("initialize", "do_step", "clear") if not callable(getattr(model, name, None))]
        if missing_methods:
            raise TypeError(
                f"{model_reference} has no {' and no '.join(missing_methods)}. A model needs initialize(), do_step(value_dict) and clear()",
            )
        return PythonModel(model_reference=model_reference, _model=model, _step_time_parameters=_step_time_parameters_of(do_step=model.do_step))

    def set_input(self, name: str, value: InterfaceValue) -> None:
        self._inputs[name] = value

    def initialize(self) -> None:
        try:
            outputs = self._model.initialize()
        except Exception as error:
            raise RuntimeError(f"The model {self.model_reference} failed in initialize(): {one_line_message(error=error)}") from error
        self._keep_outputs(method_name="initialize", outputs=outputs)

    def do_step(self, current_simulation_time: float, step_size_in_seconds: float) -> None:
        step_time = {"current_simulation_time": current_simulation_time, "step_size_in_seconds": step_size_in_seconds}
        step_time_arguments = {name: value for name, value in step_time.items() if name in self._step_time_parameters}
        # a copy, the model may change value_dict
        self._keep_outputs(method_name="do_step", outputs=self._model.do_step(dict(self._inputs), **step_time_arguments))

    def clear(self) -> None:
        self._model.clear()

    def output(self, name: str) -> InterfaceValue:
        if name not in self._outputs:
            returned = ", ".join(self._outputs) or "nothing"
            raise ValueError(f"{self.model_reference}.{self._outputs_returned_by}() returned no value for the output {name}. It returned: {returned}")
        return self._output_value(name=name, value=self._outputs[name])

    def _keep_outputs(self, method_name: str, outputs: Any) -> None:
        if not isinstance(outputs, Mapping):
            raise TypeError(
                f"{self.model_reference}.{method_name}() returned {outputs!r}. It has to return a dictionary with every output, "
                + 'for example {"temperature": 21.0}',
            )
        self._outputs = outputs
        self._outputs_returned_by = method_name

    def _output_value(self, name: str, value: Any) -> InterfaceValue:
        # numpy numbers cannot be stored as JSON
        if isinstance(value, list):
            return self._output_list(name=name, values=value)
        return self._output_number(name=name, value=value, is_in_a_list=False)

    def _output_list(self, name: str, values: list[Any]) -> FloatMatrix:
        if values and all(isinstance(value, list) for value in values):
            return [self._output_list(name=name, values=value) for value in values]
        return [self._output_number(name=name, value=value, is_in_a_list=True) for value in values]

    def _output_number(self, name: str, value: Any, is_in_a_list: bool) -> float:
        with suppress(TypeError, ValueError):
            # float() also takes a numpy array with one value
            if value is not None and not isinstance(value, (str, bytes)) and getattr(value, "ndim", 0) == 0:
                return float(value)
        returned = f"a list with {value!r}" if is_in_a_list else repr(value)
        raise TypeError(
            f"{self.model_reference}.{self._outputs_returned_by}() returned {returned} for the output {name}. "
            + "An output has to be a number or a list of numbers",
        )


def _step_time_parameters_of(do_step: Any) -> frozenset[str]:
    # inspect.signature() evaluates the annotations on Python 3.14
    code = getattr(inspect.unwrap(do_step), "__code__", None)
    if code is None:
        return frozenset()
    keyword_names = code.co_varnames[code.co_posonlyargcount : code.co_argcount + code.co_kwonlyargcount]
    return frozenset({"current_simulation_time", "step_size_in_seconds"}.intersection(keyword_names))
