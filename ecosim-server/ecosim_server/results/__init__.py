"""Reads the results of a run as one table."""

from ecosim_server.results.database_results import read_database_results
from ecosim_server.results.file_results import read_file_results
from ecosim_server.results.result_column import ResultColumn
from ecosim_server.results.result_table import ResultTable

__all__ = ["ResultColumn", "ResultTable", "read_database_results", "read_file_results"]
