import uuid

import distributed as dd
import pytest
from distributed import Variable
from ecosim_common.tech.structures.dask_variable_initializer import DaskVariableInitializer


@pytest.fixture
def unique_name() -> str:
    return f"test_variable_{uuid.uuid4()}"


def test_exists_is_false_for_unknown_variable(
    dask_client: dd.Client,
    unique_name: str,
) -> None:
    assert DaskVariableInitializer.exists(Variable(name=unique_name)) is False


def test_exists_is_true_after_set(
    dask_client: dd.Client,
    unique_name: str,
) -> None:
    variable = Variable(name=unique_name)
    variable.set(42)
    assert DaskVariableInitializer.exists(variable) is True


def test_initialize_sets_value_when_variable_is_absent(
    dask_client: dd.Client,
    unique_name: str,
) -> None:
    variable = Variable(name=unique_name)
    DaskVariableInitializer.initialize(
        variable=variable,
        value_supplier=lambda: 7,
        may_already_exist=True,
    )
    assert variable.get() == 7


def test_initialize_keeps_value_of_existing_variable(
    dask_client: dd.Client,
    unique_name: str,
) -> None:
    variable = Variable(name=unique_name)
    variable.set(1)
    DaskVariableInitializer.initialize(
        variable=variable,
        value_supplier=lambda: 2,
        may_already_exist=True,
    )
    assert variable.get() == 1


def test_initialize_skips_existence_check_for_fresh_variable(
    dask_client: dd.Client,
    unique_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_on_get(*args: object, **kwargs: object) -> None:
        pytest.fail("the value of a freshly named variable must never be read")

    monkeypatch.setattr(Variable, "get", fail_on_get)
    variable = Variable(name=unique_name)
    DaskVariableInitializer.initialize(
        variable=variable,
        value_supplier=lambda: 5,
        may_already_exist=False,
    )
    assert DaskVariableInitializer.exists(variable) is True


def test_initialize_never_reads_the_variable_value(
    dask_client: dd.Client,
    unique_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blocking read is what floods the scheduler log with TimeoutError tracebacks."""
    variable = Variable(name=unique_name)
    variable.set(1)
    monkeypatch.setattr(
        Variable,
        "get",
        lambda *args, **kwargs: pytest.fail("existence must be asked from the scheduler, not read"),
    )
    DaskVariableInitializer.initialize(
        variable=variable,
        value_supplier=lambda: 2,
        may_already_exist=True,
    )
