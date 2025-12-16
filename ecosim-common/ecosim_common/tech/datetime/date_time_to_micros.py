import datetime


def date_time_to_micros_since_unix_epoch(date_time: datetime.datetime) -> int:
    return round(date_time.timestamp() * 1_000_000)


def micros_since_unix_epoch_to_date_time(micros: int | str) -> datetime.datetime:
    micros = int(micros)
    result = datetime.datetime.fromtimestamp(micros / 1_000_000, tz=datetime.timezone.utc)
    result = result + datetime.timedelta(
        microseconds=micros - result.timestamp() * 1_000_000,
    )
    return result
