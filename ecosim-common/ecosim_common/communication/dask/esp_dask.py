import uuid

import dask.distributed as dd
from ecosim_common.communication.binary_message.binary_message import BinaryMessage, BinaryMessageHeader
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.tech.atomic.atomic_integer import AtomicInteger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


def create_internal_dask_id() -> str:
    internal_dask_id = uuid.uuid4().hex
    return internal_dask_id


# TODO_OSR: unused raw_dask_id
def is_raw_dask_client_connected(raw_dask_id: str) -> bool:
    dask_client = dd.get_client()
    if dask_client.status == "running":
        return True
    else:
        return False


# TODO_OSR: refactor to dataclass
class ESPDask(ShutdownListener):
    _logger = ESPLogger("ESPDask")

    def __init__(
        self,
        internal_dask_id: str,
    ) -> None:
        ShutdownManager().register_listener(self)
        self._closing_calls = AtomicInteger.dask(0)
        self._closed: dd.Event = dd.Event()
        self._internal_dask_id = internal_dask_id
        self._connected: bool = is_raw_dask_client_connected(internal_dask_id)
        self._origin_id: int = uuid.uuid4().int & (1 << 64) - 1

    def dask_id(self) -> str:
        return self._internal_dask_id

    def on_app_shutdown(self) -> None:
        if not self._closed.is_set():
            ESPDask._logger.info("Internal shutdown singal triggered - closing Dask client...")
            self.close()

    def connect(
        self,
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
                except TimeoutError:
                    ESPDask._logger.info("Already disconnected from Dask Client.")
            else:
                ESPDask._logger.info("Disconnection to Dask Client already in progress.")
        except dd.comm.core.CommClosedError:
            ESPDask._logger.info("Dask client already closed.")

    def send(
        self,
        message: BinaryMessage,
    ) -> None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        dask_client = dd.get_client()
        ESPDask._logger.debug(f"Sending messages {message.header().message_type} from {self._origin_id}")
        ESPDask.send_to_dask_client(dask_client, message, self._internal_dask_id, self._origin_id)

    def receive(
        self,
    ) -> ReceivedBinaryMessage | None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        dask_client = dd.get_client()
        return ESPDask.receive_from_dask_client(dask_client, self._internal_dask_id, self._origin_id)

    @staticmethod
    def send_to_dask_client(
        connection: dd.Client,
        message: BinaryMessage,
        dask_id: str,
        origin_id: int,
    ) -> None:
        ESPDask._logger.debug(f"Sending to dask_id {dask_id} and origin_id {origin_id} binary message of type {message.header().message_type}...")
        data_var = dd.Queue(name=dask_id, client=connection)
        data_var.put((message.raw_message(), origin_id))
        ESPDask._logger.debug(
            f"Sending to dask_id {dask_id} and origin_id {origin_id} binary message of type {message.header().message_type}...done.",
        )

    @staticmethod
    def receive_from_dask_client(
        connection: dd.Client,
        dask_id: str,
        origin_id: int,
    ) -> ReceivedBinaryMessage | None:
        while True:
            received_id = None
            ESPDask._logger.debug(f"Trying to receive for dask_id {dask_id} and origin_id {origin_id}...")
            try:
                data_var = dd.Queue(name=dask_id, client=connection)
                raw_message = data_var.get(timeout=300)
            except TimeoutError:
                ESPDask._logger.debug(f"Received no data at {origin_id} after 300 seconds.")
                return None
            except Exception as e:
                ESPDask._logger.error(f"Received error non-timeout error while waiting at origin_id {origin_id}: {e}")
                raise e
            ESPDask._logger.debug(f"Trying to receive for dask_id {dask_id} and origin_id {origin_id}...done.")
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
            raw_header = raw_message[0 : BinaryMessage.HEADER_BYTES]
            message_header = BinaryMessageHeader(raw_header)
            if not message_header:
                ESPDask._logger.debug("Received no valid header")
                return None
            data: bytes = raw_message[BinaryMessage.HEADER_BYTES :]
            ESPDask._logger.debug(f"Received message of type {message_header.message_type} at {origin_id} from {received_id}")
            return ReceivedBinaryMessage(message_header, data, ConnectionAddress.of_dask_client(connection))
