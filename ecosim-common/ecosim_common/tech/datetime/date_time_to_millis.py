import datetime


def date_time_to_millis_since_unix_epoch(date_time: datetime.datetime) -> int:
    return round(date_time.timestamp() * 1000)


def millis_since_unix_epoch_to_date_time(millis: int | str) -> datetime.datetime:
    millis = int(millis)
    result = datetime.datetime.fromtimestamp(millis / 1000, tz=datetime.timezone.utc)
    result = result + datetime.timedelta(
        milliseconds=millis - result.timestamp() * 1000,
    )
    return result
