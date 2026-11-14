import importlib

import pytest
from config import REPO_ROOT
from config_reference.keys import Key, enum_members, extract_keys, render_keys
from config_reference.sections import client_type_values, render_client_types
from generate_config_reference import CLIENT_TYPE_FILE, render_page, trim_simulation

CLIENT_TYPE_SOURCE = """
class ClientType(Enum):
    FMU_2 = ("fmu_2", ("fmu", "fmu2"))
    Matlab = "matlab"

    def __init__(self, serialized, alternatives=None):
        self.serialized = serialized
"""
SOURCE = """
class DatabaseConfig:
    _default_directory: ClassVar[Path] = Path("simulation_results")

def read(config, override):
    host = config.get_string("server", "host", default="localhost")
    port = config.get_int("server", "port")
    port_again = config.get_int("server", "port")
    ssl = config.get_bool("database", "ssl")
    files = config.get_string_array("fmu", "fmu_file")
    kind = config.get_string("database", "type", Storage.POSTGRES.value)
    directory = config.get_string("database", "directory", DatabaseConfig._default_directory.name)
    protocol = config.get_enum(Protocol, "server", "communication_protocol", Protocol.TCP_SOCKET)
    other = config.get_string(section_name, "dynamic")
"""
ENUMS = {"Protocol": {"DASK": "dask", "TCP_SOCKET": "tcp_socket"}, "Storage": {"POSTGRES": "postgres"}}


def test_extract_keys_reads_section_key_type_and_default() -> None:
    assert extract_keys(SOURCE, ENUMS) == [
        Key("server", "host", "string", "localhost"),
        Key("server", "port", "integer", None),
        Key("database", "ssl", "boolean", None),
        Key("fmu", "fmu_file", "list", None),
        Key("database", "type", "string", "postgres"),
        Key("database", "directory", "string", "simulation_results"),
        Key("server", "communication_protocol", "one of `DASK`, `TCP_SOCKET`", "TCP_SOCKET"),
    ]


def test_enum_members_maps_names_to_values() -> None:
    source = "class Protocol(str, Enum):\n    DASK = 'dask'\n    TCP_SOCKET = 'tcp_socket'\n\n    def of(self): pass\n"

    assert enum_members(source) == {"Protocol": {"DASK": "dask", "TCP_SOCKET": "tcp_socket"}}


def test_render_keys_marks_required_keys() -> None:
    table = render_keys([Key("server", "host", "string", "localhost"), Key("server", "port", "integer", None)])

    assert "| `server` | `host` | string | `localhost` |" in table
    assert "| `server` | `port` | integer | required |" in table


def test_a_key_read_only_for_postgres_results_is_required_only_for_postgres() -> None:
    source = 'def _for_postgres(config):\n    host = config.get_string("database", "server")\n'

    assert render_keys(extract_keys(source, ENUMS)).splitlines()[-1] == "| `database` | `server` | string | required for PostgreSQL |"


def test_render_keys_writes_out_an_empty_default() -> None:
    key = Key(section="database", key="password", type="string", default="")

    assert "| `database` | `password` | string | empty |" in render_keys([key])


def test_trim_simulation_keeps_the_first_simulator_and_two_interfaces() -> None:
    config = {"simulators": [{"name": "a", "interfaces": [1, 2, 3]}, {"name": "b"}], "setup": {"delta_t": 60000}}

    assert trim_simulation(config) == {"simulators": [{"name": "a", "interfaces": [1, 2]}], "setup": {"delta_t": 60000}}


def test_client_type_values_reads_every_member_with_its_alternatives() -> None:
    assert client_type_values(CLIENT_TYPE_SOURCE) == [["fmu_2", "fmu", "fmu2"], ["matlab"]]


def test_client_type_values_rejects_a_member_it_cannot_read() -> None:
    with pytest.raises(ValueError):
        client_type_values("class ClientType(Enum):\n    FMU_2 = build_member()\n")


def test_client_type_values_agree_with_client_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(REPO_ROOT / "ecosim-common")
    client_type = importlib.import_module("ecosim_common.client.config.client_type").ClientType

    values = client_type_values(CLIENT_TYPE_FILE.read_text(encoding="utf-8"))

    assert len(values) == len(client_type)
    for member, accepted in zip(client_type, values):
        assert accepted[0] == member.serialized
        assert all(client_type.of_string(value) is member for value in accepted)


def test_render_client_types_lists_the_alternatives() -> None:
    table = render_client_types([["fmu_2", "fmu", "fmu2"], ["matlab"]])

    assert "| `fmu_2` | `fmu`, `fmu2` |" in table
    assert "| `matlab` |  |" in table


def test_render_page_lists_the_client_types_of_the_code() -> None:
    page = render_page()

    assert "| `fmu_2` | `fmu`, `fmu2` |" in page
    assert "| `fmu_3` | `fmu3` |" in page
    assert "| `matlab` |  |" in page
    assert "| `pyro5` | `pyro` |" in page
