from typing import Generator, cast, Any, assert_never

import pytest

from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


@pytest.fixture(
    scope="function",
    # params=[ESPStructureType.SIMPLE, ESPStructureType.DASK_VARIABLE, ESPStructureType.DASK_ACTOR, ESPStructureType.THREAD],
    params=[ESPStructureType.SIMPLE, ESPStructureType.DASK_VARIABLE, ESPStructureType.THREAD],
)
def esp_structure_type(request: pytest.FixtureRequest) -> Generator[ESPStructureType, Any, None]:
    esp_map_type: ESPStructureType = cast(ESPStructureType, request.param)
    match esp_map_type:
        # case ESPStructureType.DASK_ACTOR | ESPStructureType.DASK_VARIABLE:
        #     request.getfixturevalue("dask_client")
        case ESPStructureType.DASK_VARIABLE:
            request.getfixturevalue("dask_client")
        case ESPStructureType.SIMPLE:
            pass
        case ESPStructureType.THREAD:
            pass
        case _:
            assert_never(esp_map_type)

    yield esp_map_type
