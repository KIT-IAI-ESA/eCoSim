import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.main import main
from ecosim_test_common.exit_code_and_error_line import exit_code_and_error_line
from ecosim_test_common.resources.config_files import config_file_path_str

REQUIRED_ARGUMENTS = [
    "--server-config",
    config_file_path_str("server_config.ini"),
    "--simulation-config",
    config_file_path_str("simulation.json"),
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
    arguments = [*REQUIRED_ARGUMENTS, option, value]

    exit_code, error_line = exit_code_and_error_line(command=lambda: CLIArguments(passed_arguments=arguments), capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert f"error: argument {option}: " in error_line


@pytest.mark.parametrize("value", ["TCP_SOCKET", "tcp_socket", "tcp-socket"])
def test_the_communication_protocol_ignores_case_and_takes_a_hyphen(value: str) -> None:
    arguments = CLIArguments(passed_arguments=[*REQUIRED_ARGUMENTS, "--communication-protocol", value])

    assert arguments.communication_protocol() is CommunicationProtocol.TCP_SOCKET


def test_the_help_does_not_print_the_banner(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=["--help"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.startswith("usage: ecosim-server --server-config FILE --simulation-config FILE [options]")
