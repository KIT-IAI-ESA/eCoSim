from config_reference_keys import Key, enum_members, extract_keys, render_keys
from generate_config_reference import trim_simulation

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


def test_trim_simulation_keeps_the_first_simulator_and_two_interfaces() -> None:
    config = {"simulators": [{"name": "a", "interfaces": [1, 2, 3]}, {"name": "b"}], "setup": {"delta_t": 60000}}

    assert trim_simulation(config) == {"simulators": [{"name": "a", "interfaces": [1, 2]}], "setup": {"delta_t": 60000}}
