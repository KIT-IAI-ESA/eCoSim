import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_test_common.resources.config_files import config_file_path_str

REQUIRED_ARGUMENTS = [
    "--server-config",
    config_file_path_str("server_config.ini"),
    "--simulation-config",
    config_file_path_str("simulation.json"),
    "--steps",
    "100",
]


@pytest.mark.parametrize(
    "option, value",
    [
        ("--steps", "0"),
        ("--steps", "-3"),
        ("--step-size", "0"),
        ("--pace", "2"),
        ("--port", "70000"),
        ("--database-ssl", "maybe"),
        ("--communication-protocol", "udp"),
    ],
)
def test_a_value_that_would_start_a_wrong_run_stops_the_server_with_a_usage_error(
    capsys: pytest.CaptureFixture[str],
    option: str,
    value: str,
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        CLIArguments(passed_arguments=[*REQUIRED_ARGUMENTS, option, value])

    assert exit_info.value.code == 2
    assert f"error: argument {option}: " in capsys.readouterr().err.splitlines()[-1]


@pytest.mark.parametrize("value", ["TCP_SOCKET", "tcp_socket", "tcp-socket"])
def test_the_communication_protocol_takes_the_spellings_it_took_before(value: str) -> None:
    arguments = CLIArguments(passed_arguments=[*REQUIRED_ARGUMENTS, "--communication-protocol", value])

    assert arguments.communication_protocol() is CommunicationProtocol.TCP_SOCKET
