from dataclasses import dataclass, field

from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass
class HPCClientState:
    client_id: ClientID
    config_override: ClientConfigOverride
    config_parser: ConfigParser
    is_boot_strapping_done: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    was_started_event: ParallelEvent | None = None
