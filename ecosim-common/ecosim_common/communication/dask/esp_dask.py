import dask.distributed as dd
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.dask.dask_messages import DaskMessage, ReceivedMessage, DaskMessageHeader
from ecosim_common.tech.atomic.atomic_integer import AtomicIntegerDask
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownManager, ShutdownListener
from ecosim_common.config.client_id import ClientID


def create_internal_dask_client() -> dd.Client:
    create_internal_dask_client = dd.get_client()
    return create_internal_dask_client


def is_raw_dask_client_connected(raw_dask_client: dd.Client) -> bool:
    if raw_dask_client.status == 'running':
        return True
    else:
        return False


class ESPDask(ShutdownListener):
    _logger = ESPLogger("ESPDask")

    def __init__(self):
        ShutdownManager().register_listener(self)
        self._closing_calls = AtomicIntegerDask(0)
        self._closed: dd.Event = dd.Event()
        internal_dask_client = dd.get_client()
        if internal_dask_client.status == 'running':
            self._connected = True
        else:
            self._connected = False

    def on_app_shutdown(self):
        if not self._closed.is_set():
            ESPDask._logger.info("Internal shutdown singal triggered - closing Dask client...")
            self.close()

    def connect(
        self,
        connection_address: ConnectionAddress,
    ) -> None:
        dask_client = dd.get_client()
        if dask_client.scheduler.address == f"tcp://{connection_address.__str__}":
            self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def connection_address(self) -> ConnectionAddress:
        dask_client = dd.get_client()
        return ConnectionAddress.of_dask_client(dask_client)

    def close(self) -> None:
        try:
            if self._closed.is_set():
                if not ShutdownManager.shutdown_event.is_set():
                    ESPDask._logger.warning("Tried to close an already closed connection to Dask client.")
                return
            closing_calls = self._closing_calls.inc()
            self._closed.set()
            self._connected = False
            if closing_calls == 1:
                # self._internal_dask_client = None

                ESPDask._logger.info("Successfully disconnected from Dask client.")
            else:
                ESPDask._logger.info("Disconnection to Dask Client already in progress.")
        except RuntimeError or dd.comm.core.CommClosedError:
            ESPDask._logger.info("Dask client already closed.")

    def send(
        self,
        message: DaskMessage,
        client_id: ClientID,
    ) -> None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        dask_client = dd.get_client()
        ESPDask._logger.debug(f"Sending messages {message.header().message_type}")
        ESPDask.send_to_dask_client(dask_client, message, client_id)

    def receive(
        self,
        client_id: ClientID,
    ) -> ReceivedMessage | None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        dask_client = dd.get_client()
        return ESPDask.receive_from_dask_client(dask_client, client_id)

    @staticmethod
    def send_to_dask_client(
        connection: dd.Client,
        message: DaskMessage,
        client_id: ClientID,
    ) -> None:
        if client_id.to_str() in connection.list_datasets():
            connection.unpublish_dataset(client_id.to_str())
        connection.datasets[client_id.to_str()] = message.raw_message()

    @staticmethod
    def receive_from_dask_client(
        connection: dd.Client,
        client_id: ClientID,
    ) -> ReceivedMessage | None:
        while True:
            if client_id.to_str() not in connection.list_datasets():
                continue
            raw_message = connection.get_dataset(client_id.to_str())
            if not raw_message:
                ESPDask._logger.debug("Received no data")
                return None
            connection.unpublish_dataset(client_id.to_str())
            connection.datasets[client_id.to_str()] = None
            raw_header = raw_message[0:DaskMessage.HEADER_BYTES]
            message_header = DaskMessageHeader(raw_header)
            if not message_header:
                ESPDask._logger.debug("Received no valid header")
                return None
            data: bytes = raw_message[DaskMessage.HEADER_BYTES:]
            while len(data) < message_header.data_length:
                chunk = raw_message[DaskMessage.HEADER_BYTES:message_header.data_length - len(data)]
                if not chunk:
                    raise ConnectionError("Error while receiving junks.")
                data += chunk
            ESPDask._logger.debug(f"Received message of type {message_header.message_type}")
            return ReceivedMessage(message_header, data, ConnectionAddress.of_dask_client(connection))
