import dataclasses
from typing import Mapping

from websockets import ServerConnection

from ecosim_common.config.client_id import ClientID


@dataclasses.dataclass(frozen=True)
class RenderingMessageClientHeader:
    client_id: str

    def is_simulator(self) -> bool:
        return self.client_id != "sim_control"

    @staticmethod
    def of_connection(connection: ServerConnection) -> 'RenderingMessageClientHeader':
        if not connection.request or not connection.request.headers:
            raise RuntimeError(f"Missing request or request header: {connection}.")
        return RenderingMessageClientHeader(connection.request.headers['client_id'])

    @staticmethod
    def create_raw(
            client_id: ClientID,
    ) -> Mapping[str, str]:
        return {
            'client_id': client_id.to_str(),
        }
