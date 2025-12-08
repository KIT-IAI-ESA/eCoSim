import datetime

from ecosim_common.tech.datetime.date_time_to_millis import (
    date_time_to_millis_since_unix_epoch,
    millis_since_unix_epoch_to_date_time,
)


def test_date_time_to_millis() -> None:
    date_time = datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone.utc,
    )
    millis = date_time_to_millis_since_unix_epoch(date_time)
    assert millis == 1742566293123


def test_millis_to_date_time() -> None:
    millis = 1742566293123
    date_time = millis_since_unix_epoch_to_date_time(millis)
    assert date_time == datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone.utc,
    )


def test_date_time_to_millis_and_back() -> None:
    date_time = datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone.utc,
    )
    millis = date_time_to_millis_since_unix_epoch(date_time)
    restored = millis_since_unix_epoch_to_date_time(millis)
    assert restored == date_time


def test_millis_to_date_time_and_back() -> None:
    millis = 1742566293123
    date_time = millis_since_unix_epoch_to_date_time(millis)
    restored = date_time_to_millis_since_unix_epoch(date_time)
    assert restored == millis


def test_date_time_to_millis_and_back_with_tz() -> None:
    date_time = datetime.datetime(
        2025,
        3,
        21,
        14,
        11,
        33,
        123_000,
        tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
    )
    millis = date_time_to_millis_since_unix_epoch(date_time)
    restored = millis_since_unix_epoch_to_date_time(millis)
    assert restored == date_time
    assert restored.tzinfo == datetime.timezone.utc
