from dataclasses import dataclass, field

from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass
class HPCClientState:
    simulator_name: str
    config_override: ClientConfigOverride
    is_boot_strapping_done: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    config_parser: ConfigParser | None = None
    was_started_event: ParallelEvent | None = None
