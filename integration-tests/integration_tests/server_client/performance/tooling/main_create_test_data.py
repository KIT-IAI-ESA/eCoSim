import argparse
import sys
from datetime import datetime
from typing import Sequence

from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.performance_mean_statistics import PerformanceMeanStatistics
from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories
from integration_tests.server_client.performance.tooling.performance_setup import FILE_NAME_DATE_TIME_FORMAT, current_machine
from integration_tests.tech.integration_test_resource_utils import performance_data_resource_path


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # argparse formats the help with '%', so the '%' of the format must be escaped
    parser.add_argument("--since", required=True, help=f"start of the first run ({FILE_NAME_DATE_TIME_FORMAT})".replace("%", "%%"))
    since = datetime.strptime(parser.parse_args(argv).since, FILE_NAME_DATE_TIME_FORMAT)
    machine_name, now = current_machine(), datetime.now()
    statistics = PerformanceMeanStatistics(PerformanceRepositories.create())
    for protocol in CommunicationProtocol:
        save_path = performance_data_resource_path() / f"{now.strftime(FILE_NAME_DATE_TIME_FORMAT)}_{protocol.serialized}_{machine_name}.jsonl"
        statistics.calculate_and_save_mean_of_actual_since(machine_name, since, protocol, now, save_path)
        # without results of a protocol, nothing is saved
        print(f"saved {save_path}" if save_path.exists() else f"no results of {protocol.serialized}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
