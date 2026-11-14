from argparse import Namespace
from pathlib import Path

import pytest
from ecosim.check.check_command import build_parser
from ecosim.server_arguments import reason_to_refuse, server_arguments, split_server_options
from ecosim.simulation_command_line import SimulationCommandLine
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_test_common.test_data.building_simulation import write_building_simulation


def command_line_of(*passed_arguments: str) -> SimulationCommandLine:
    return SimulationCommandLine.of_arguments(parser=build_parser(), passed_arguments=passed_arguments, command_name="check")


def parsed_options() -> Namespace:
    return build_parser().parse_args([])


def test_the_options_after_two_dashes_are_for_the_server() -> None:
    assert split_server_options(passed_arguments=["building", "--steps", "3", "--", "--database-schema", "run_2"]) == (
        ["building", "--steps", "3"],
        ["--database-schema", "run_2"],
    )


@pytest.mark.parametrize(
    "server_option, reason",
    [
        ("--database-t=file", "--database-type after -- is set by ecosim check. Use ecosim check --database-type instead."),
        ("--deb", "--debug after -- is set by ecosim check. Use ecosim check --debug instead."),
        ("--host", "--host after -- is set by ecosim check. Leave it out."),
    ],
)
def test_an_option_that_the_command_gives_the_server_itself_is_refused_after_two_dashes(server_option: str, reason: str) -> None:
    assert reason_to_refuse(server_options=[server_option, "1234"], command_name="check", command_options=parsed_options()) == reason


def test_an_option_of_the_server_alone_passes_after_two_dashes() -> None:
    server_options = ["--database-schema", "run_2", "--database-drop-existing-schema"]

    assert reason_to_refuse(server_options=server_options, command_name="check", command_options=parsed_options()) is None


def test_a_misspelt_option_after_two_dashes_is_a_usage_error_of_the_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(folder=tmp_path)

    with pytest.raises(SystemExit) as exit_info:
        command_line_of(str(simulation), "--", "--database-schma", "run_2")

    assert exit_info.value.code == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "ecosim check: error: unrecognized arguments: --database-schma run_2. Did you mean --database-schema instead of --database-schma?"
    )


def test_the_options_of_the_command_reach_the_server_with_the_same_values(tmp_path: Path) -> None:
    simulation = write_building_simulation(folder=tmp_path)
    command_line = command_line_of(
        str(simulation),
        "--duration",
        "1d",
        "--step-size",
        "15min",
        "--pace",
        "0.5",
        "--debug",
        "--",
        "--database-schema",
        "run_2",
    )

    arguments = CLIArguments(
        passed_arguments=server_arguments(
            simulation=command_line.simulation,
            run_options=command_line.run_options,
            port=4321,
            database_directory=tmp_path / "results",
        ),
    )

    assert (arguments.simulation_steps(), arguments.step_size_override(), arguments.pace(), arguments.debug_enabled(), arguments.port) == (
        96,
        900_000,
        0.5,
        True,
        4321,
    )
    assert arguments.db_config_overwrite().schema(default="") == "run_2"


def test_the_results_go_to_files_unless_the_server_config_sets_a_type(tmp_path: Path) -> None:
    simulation = write_building_simulation(folder=tmp_path)
    command_line = command_line_of(str(simulation))
    files_by_default = CLIArguments(
        passed_arguments=server_arguments(
            simulation=command_line.simulation,
            run_options=command_line.run_options,
            port=4321,
            database_directory=tmp_path,
        ),
    )
    with (simulation / "server" / "preferences.ini").open("a", encoding="utf-8") as server_config:
        server_config.write("type=postgres\n")

    as_configured = CLIArguments(
        passed_arguments=server_arguments(
            simulation=command_line.simulation,
            run_options=command_line.run_options,
            port=4321,
            database_directory=tmp_path,
        ),
    )

    assert (files_by_default.database_type(), as_configured.database_type()) == (DatabaseType.FILE, None)
