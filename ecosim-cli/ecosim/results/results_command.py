import argparse
import os
from pathlib import Path
from typing import Sequence

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER
from ecosim_common.tech.readable_count import readable_count
from ecosim_server.results import ResultTable

from ecosim.command import command_parser
from ecosim.report_lines import shown_path
from ecosim.results.results_overview import overview_lines
from ecosim.results.results_source import ResultsSource, add_source_options, reason_not_to_read


def build_parser() -> EcosimArgumentParser:
    parser = command_parser(
        name="results",
        description="Shows the results of a run with the minimum, mean and maximum of every output. "
        + "With --csv it writes them as one table to a CSV file.",
        examples=(
            "ecosim results building",
            "ecosim results building --csv results.csv",
            "ecosim results building --interface house.T_indoor --interface weather --csv temperatures.csv",
            "ecosim results --server-config building/server/preferences.ini --database-schema run_2",
        ),
    )
    parser.usage = "%(prog)s [options] [FOLDER]"
    simulation_config = AppConfigParameter(
        name="simulation-config",
        metavar="FILE",
        help_text="The simulation config of the run. Only needed for results in PostgreSQL, or for a folder without a copy of it.",
    )
    parser.add_parameters(parameters=[DEBUG_PARAMETER, simulation_config], environment_variables=os.environ)
    _add_table_options(parser=parser)
    add_source_options(parser=parser)
    return parser


def _add_table_options(parser: EcosimArgumentParser) -> None:
    table_options = parser.add_argument_group(title="table")
    table_options.add_argument("--inputs", action="store_true", help="Show the inputs too.")
    table_options.add_argument(
        "--interface",
        metavar="NAME",
        action="append",
        help="Show only this column, or all columns of a simulator or an array. Can be given several times.",
    )
    table_options.add_argument("--csv", metavar="FILE", help="Write the shown columns to this CSV file.")


def main(passed_arguments: Sequence[str]) -> int:
    parser = build_parser()
    if "--" in passed_arguments:
        parser.error("leave out the -- before the --database options. ecosim results takes them itself")
    options = parser.parse_args(passed_arguments)
    reason = reason_not_to_read(options=options)
    if reason is not None:
        parser.error(reason)
    source = ResultsSource.of_options(options=options)
    _show(table=source.read(simulation_config=options.simulation_config), source=source, options=options)
    return 0


def shown_columns(table: ResultTable, interface_names: Sequence[str], include_inputs: bool) -> ResultTable:
    shown = table if include_inputs else table.without_inputs()
    for name in interface_names:
        if not shown.matches(name=name) and table.matches(name=name):
            raise ValueError(f"{name} is an input. Add --inputs to show inputs.")
    return shown.select(names=interface_names) if interface_names else shown


def _show(table: ResultTable, source: ResultsSource, options: argparse.Namespace) -> None:
    interface_names = options.interface or []
    shown = shown_columns(table=table, interface_names=interface_names, include_inputs=options.inputs)
    left_out_inputs = 0 if options.inputs or interface_names else sum(column.is_input for column in table.columns)
    print("\n".join([*overview_lines(table=shown, source=source.description(), left_out_inputs=left_out_inputs), ""]))
    if options.csv is None:
        print("Add --csv results.csv to write the table to a file.")
        return
    shown.write_csv(file=Path(options.csv))
    rows, columns = readable_count(count=len(shown.rows), noun="row"), readable_count(count=len(shown.columns), noun="column")
    print(f"Wrote {rows} and {columns} to {shown_path(path=Path(options.csv))}.")
