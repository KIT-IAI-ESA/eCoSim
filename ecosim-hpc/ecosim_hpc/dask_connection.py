from pathlib import Path

from dask import distributed
from distributed.utils import get_ip_interface
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments


def connect_or_start_dask_cluster(cli_arguments: HPCServerCliArguments) -> distributed.Client:
    """In batch mode only MPI rank 1 returns: the scheduler and worker ranks block in 'initialize' and then exit."""
    if cli_arguments.interactive():
        return _connect_to_running_scheduler(cli_arguments.scheduler_file())
    return _start_mpi_cluster(
        network_interface=cli_arguments.network_interface(),
        threads_per_worker=cli_arguments.threads_per_worker(),
    )


def _connect_to_running_scheduler(scheduler_file: Path) -> distributed.Client:
    # the Dask client would wait forever for a missing file
    if not scheduler_file.is_file():
        raise SystemExit(f"The scheduler file '{scheduler_file}' does not exist. Start the Dask scheduler first or set --scheduler-file.")
    return distributed.Client(scheduler_file=str(scheduler_file))


def _start_mpi_cluster(network_interface: str | None, threads_per_worker: int | None) -> distributed.Client:
    from dask_mpi import initialize

    _reject_unknown_network_interface(network_interface)
    options = {"interface": network_interface, "nthreads": threads_per_worker}
    # an explicit nthreads=None is not the default of dask_mpi, it gives every worker all CPUs
    initialize(**{name: value for name, value in options.items() if value is not None})
    return distributed.Client()


def _reject_unknown_network_interface(network_interface: str | None) -> None:
    # get_ip_interface raises on an unknown interface: fail here, before MPI starts, or the other ranks wait forever
    if network_interface is not None:
        get_ip_interface(network_interface)
