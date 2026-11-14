"""Reads the results of a run as one table. The one part of eCoSim that is meant to be used from Python."""

from ecosim_server.results.file_results import read_results
from ecosim_server.results.result_column import ResultColumn
from ecosim_server.results.result_table import ResultTable

__all__ = ["ResultColumn", "ResultTable", "read_results"]
