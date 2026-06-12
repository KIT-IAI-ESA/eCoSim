import dask.distributed as dd
import uuid
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.dask.dask_messages import DaskMessage, ReceivedMessage, DaskMessageHeader
from ecosim_common.tech.atomic.atomic_integer import AtomicIntegerDask
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownManager, ShutdownListener


def create_internal_dask_id() -> str:
    internal_dask_id = uuid.uuid4().hex
    return internal_dask_id


def is_raw_dask_client_connected(raw_dask_id: str) -> bool:
    dask_client = dd.get_client()
    if dask_client.status == "running":
        return True
    else:
        return False
    # if raw_dask_id in dask_client.datasets.keys():
    #     return True
    # else:
    #     return False
    # try:
    #     data_var = dd.Variable(raw_dask_id,dask_client)
    #     data_var.get(timeout=10)
    #     return True
    # except TimeoutError:
    #     return False


class ESPDask(ShutdownListener):
    _logger = ESPLogger("ESPDask")

    def __init__(
            self,
            internal_dask_id: str,
    ) -> None:
        ShutdownManager().register_listener(self)
        self._closing_calls = AtomicIntegerDask(0)
        self._closed: dd.Event = dd.Event()
        self._internal_dask_id = internal_dask_id
        self._connected: bool = is_raw_dask_client_connected(internal_dask_id)
        self._origin_id: int = uuid.uuid4().int & (1 << 64) - 1

    def on_app_shutdown(self) -> None:
        if not self._closed.is_set():
            ESPDask._logger.info("Internal shutdown singal triggered - closing Dask client...")
            self.close()

    def connect(
        self,
        connection_address: ConnectionAddress,
    ) -> None:
        dask_client = dd.get_client()
        dd.Queue(name=self._internal_dask_id, client=dask_client)
        dask_client.datasets[self._internal_dask_id] = None
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def connection_address(self) -> ConnectionAddress:
        dask_client = dd.get_client()
        return ConnectionAddress.of_dask_client(dask_client)

    def close(self) -> None:
        try:
            if self._closed.is_set():
                if not ShutdownManager().shutdown_event.is_set():
                    ESPDask._logger.warning("Tried to close an already closed connection to Dask client.")
                return
            closing_calls = self._closing_calls.inc()
            self._closed.set()
            self._connected = False
            if closing_calls == 1:
                dask_client = dd.get_client()
                try:
                    data_var = dd.Queue(name=self._internal_dask_id, client=dask_client)
                    if data_var.qsize == 1:
                        data_var.get()
                    data_var.put("empty")
                    ESPDask._logger.info("Successfully disconnected from Dask client.")
                # else:
                except TimeoutError:
                    ESPDask._logger.info("Already disconnected from Dask Client.")
            else:
                ESPDask._logger.info("Disconnection to Dask Client already in progress.")
        except dd.comm.core.CommClosedError:
            ESPDask._logger.info("Dask client already closed.")

    def send(
        self,
        message: DaskMessage,
    ) -> None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        dask_client = dd.get_client()
        ESPDask._logger.debug(f"Sending messages {message.header().message_type} from {self._origin_id}")
        ESPDask.send_to_dask_client(dask_client, message, self._internal_dask_id, self._origin_id)

    def receive(
        self,
    ) -> ReceivedMessage | None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        dask_client = dd.get_client()
        return ESPDask.receive_from_dask_client(dask_client, self._internal_dask_id, self._origin_id)

    @staticmethod
    def send_to_dask_client(
        connection: dd.Client,
        message: DaskMessage,
        dask_id: str,
        origin_id: int,
    ) -> None:
        data_var = dd.Queue(name=dask_id, client=connection)
        data_var.put((message.raw_message(), origin_id))

    @staticmethod
    def receive_from_dask_client(
        connection: dd.Client,
        dask_id: str,
        origin_id: int,
    ) -> ReceivedMessage | None:
        while True:
            received_id = None
            data_var = dd.Queue(name=dask_id, client=connection)
            try:
                raw_message = data_var.get(timeout=300)
            except TimeoutError:
                ESPDask._logger.debug(f"Received no data at {origin_id} after 300 seconds.")
                return None
            try:
                raw_message, received_id = raw_message
            except (ValueError, TypeError):
                pass
            if not raw_message or received_id == origin_id:
                data_var.put((raw_message, received_id))
                continue
            if raw_message == "empty" or dask_id not in connection.datasets.keys():
                ESPDask._logger.debug(f"Received no data at {origin_id}")
                return None
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
            ESPDask._logger.debug(f"Received message of type {message_header.message_type} at {origin_id} from {received_id}")
            return ReceivedMessage(message_header, data, ConnectionAddress.of_dask_client(connection))
