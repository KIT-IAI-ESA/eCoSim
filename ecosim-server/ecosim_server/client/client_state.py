from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.config.client_id import ClientID
from ecosim_server.client_connection import ClientConnection
from ecosim_server.config.simulation_config import ClientSimulatorConfig


class ClientState:
    def __init__(
        self,
        client_config: ClientSimulatorConfig,
    ):
        self.client_id: ClientID = client_config.client_id
        self.connection: ClientConnection | None = None
        self.connected: bool = False
        self.interfaces_validated: bool = False
        self.step_size_accepted: bool = False
        self.simulation_started: bool = False
        self.ready_for_simulation: bool = False
        self.stopped_simulation: bool = False

    @property
    def connection_address(self) -> ConnectionAddress | None:
        if not self.connected or self.connection is None:
            return None
        return self.connection.address

    def close_connection(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            self.connected = False
