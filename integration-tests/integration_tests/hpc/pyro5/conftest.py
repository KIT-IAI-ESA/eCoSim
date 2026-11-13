import logging
import threading
from typing import Any, Generator, cast

import Pyro5.api
import pytest
from dask import distributed as dd
from ecosim_common.tech.dask.init_dask import init_dask

from integration_tests.hpc.pyro5.hpc_pyro5_setup import SCHEDULER_NODE_IP, WORKER_NODE_IPS, Pyro5CountingModel


@pytest.fixture
def pyro_port(request: pytest.FixtureRequest) -> Generator[int, Any, None]:
    """The Pyro object runs before the simulation starts, as on the cluster; eCoSim never starts it.

    It listens on 'localhost', or on the host an indirect parametrization passes.
    """
    host: str = getattr(request, "param", "localhost")
    daemon = Pyro5.api.Daemon(host=host, port=0)
    daemon.register(Pyro5CountingModel(), objectId=Pyro5CountingModel.OBJECT_NAME)
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    yield cast(int, daemon.sock.getsockname()[1])
    daemon.shutdown()


@pytest.fixture
def dask_cluster(request: pytest.FixtureRequest) -> dd.Client:
    """A cluster of the given (workers, threads per worker); the teardown hook of ecosim-test-common closes it."""
    workers, threads_per_worker = request.param
    client = dd.Client(n_workers=workers, threads_per_worker=threads_per_worker)
    init_dask(log_level=logging.DEBUG, client=client)
    return client


@pytest.fixture
def dask_cluster_on_nodes(request: pytest.FixtureRequest) -> dd.Client:
    """One worker per node, with the threads an indirect parametrization passes as {node IP: threads}; 2 by default.

    The teardown hook of ecosim-test-common closes the client and the cluster.
    """
    threads_by_node_ip: dict[str, int] = getattr(request, "param", {ip: 2 for ip in WORKER_NODE_IPS})
    cluster = dd.SpecCluster(
        scheduler={"cls": dd.Scheduler, "options": {"host": SCHEDULER_NODE_IP, "dashboard_address": ":0"}},
        workers={ip: {"cls": dd.Nanny, "options": {"host": ip, "nthreads": threads}} for ip, threads in threads_by_node_ip.items()},
    )
    return dd.Client(cluster)
