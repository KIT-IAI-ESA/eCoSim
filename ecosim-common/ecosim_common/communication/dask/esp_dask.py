import dask.distributed as dd
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.dask.dask_messages import DaskMessage, ReceivedMessage  # , DaskMessageHeader
from ecosim_common.tech.atomic.atomic_integer import AtomicInteger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownManager  # , ShutdownListener


def create_internal_dask_client() -> dd.Client:
    create_internal_dask_client = dd.get_client()
    return create_internal_dask_client


def is_raw_dask_client_connected(raw_dask_client: dd.Client) -> bool:
    if raw_dask_client.status == 'running':
        return True
    else:
        return False


class ESPDask(ShutdownManager):
    _logger = ESPLogger("ESPDask")

    def __init__(self,
                 internal_dask_client: dd.Client | None,
                ):
        ShutdownManager().register_listener(self)
        self._closing_calls = AtomicInteger(0)
        self._closed: dd.Event = dd.Event()
        self._internal_dask_client = internal_dask_client
        self._connected = is_raw_dask_client_connected(internal_dask_client)

    def on_app_shutdown(self):
        if not self._closed.is_set():
            ESPDask._logger.info("Internal shutdown singal triggered - closing Dask client...")
            self.close()

    def connect(self,
                connection_address: ConnectionAddress,
                ) -> None:
        if self._internal_dask_client.scheduler.address == f"tcp://{connection_address.__str__}":
            self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def connection_address(self) -> ConnectionAddress:
        return ConnectionAddress.of_dask_client(self._internal_dask_client)

    def close(self) -> None:
        if self._closed.is_set():
            if not ShutdownManager.shutdown_event.is_set():
                ESPDask._logger.warning("Tried to close an already closed connection to Dask client.")
            return
        closing_calls = self._closing_calls.inc()
        if closing_calls == 1:
            self._internal_dask_client = None
            ESPDask._logger.info("Successfully disconnected from Dask client.")
        else:
            ESPDask._logger.info("Disconnection to Dask Client already in progress.")

    def send(self,
             message: DaskMessage,
             ) -> None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        ESPDask._logger.debug(f"Sending messages {message.header().message_type}")
        ESPDask.send_to_dask_client(self._internal_dask_client, message)

    def receive(self) -> ReceivedMessage | None:
        if self._closed.is_set():
            raise Exception("Dask client has already or in the process of being disconnected.")
        return ESPDask.receive_from_dask_client(self._internal_dask_client)

    @staticmethod
    def send_to_dask_client(connection: dd.Client,
                       message: DaskMessage
                       ) -> None:
        dd.Variable(client=connection).set(message.raw_message())
#        #######TO DO##############

    @staticmethod
    def receive_from_dask_client(connection: dd.Client) -> ReceivedMessage | None:
        recv = dd.Variable(client=connection).get()
        print(recv)
#        #######TO DO##############
