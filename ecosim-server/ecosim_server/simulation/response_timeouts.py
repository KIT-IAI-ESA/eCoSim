from dataclasses import dataclass


@dataclass(frozen=True)
class ResponseTimeouts:
    step_response_timeout_in_seconds: float = 30
    start_response_timeout_in_seconds: float = 5
    restore_response_timeout_in_seconds: float = 60 * 60
    restore_connection_check_interval_in_seconds: float = 30
