from dataclasses import dataclass, field

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.config.client_id import ClientID
from ecosim_server.client_connection import ClientConnection
from ecosim_server.config.simulation_config import ClientSimulatorConfig


@dataclass
class ClientState:
    client_id: ClientID = field()
    connection: ClientConnection | None = None
    connected: bool = False
    interfaces_validated: bool = False
    step_size_accepted: bool = False
    simulation_started: bool = False
    ready_for_simulation: bool = False
    stopped_simulation: bool = False

    @staticmethod
    def of_client_config(
        client_config: ClientSimulatorConfig,
    ) -> "ClientState":
        return ClientState(
            client_id=client_config.client_id,
            connection=None,
            connected=False,
            interfaces_validated=False,
            step_size_accepted=False,
            simulation_started=False,
            ready_for_simulation=False,
            stopped_simulation=False,
        )

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
