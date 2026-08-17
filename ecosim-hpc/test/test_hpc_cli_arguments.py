from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.system_arguments import overwrite_system_argument
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments


def test_communication_protocol() -> None:
    overwrite_system_argument("--simulator-dir", "/path/to/simulator")
    overwrite_system_argument("--simulation-config", "/path/to/simulation/config")
    overwrite_system_argument("--server-config", "/path/to/server/config")
    overwrite_system_argument("--steps", "1000")

    cli_arguments = HPCServerCliArguments()
    assert cli_arguments.communication_protocol() == CommunicationProtocol.DASK
