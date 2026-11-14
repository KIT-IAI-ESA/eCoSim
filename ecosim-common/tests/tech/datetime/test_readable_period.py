from datetime import datetime, timedelta, timezone

import pytest

from ecosim_common.tech.datetime.readable_period import readable_period

_BERLIN_IN_WINTER = timezone(timedelta(hours=1))


@pytest.mark.parametrize(
    ("start", "end", "text"),
    [
        (
            datetime(year=2023, month=1, day=1, tzinfo=timezone.utc),
            datetime(year=2023, month=1, day=2, hour=1, tzinfo=timezone.utc),
            "2023-01-01 00:00 to 2023-01-02 01:00 UTC",
        ),
        (
            datetime(year=2023, month=1, day=1, tzinfo=timezone.utc),
            datetime(year=2023, month=1, day=1, second=4, microsecond=500_000, tzinfo=timezone.utc),
            "2023-01-01 00:00:00 to 2023-01-01 00:00:04 UTC",
        ),
        (
            datetime(year=2023, month=1, day=1, tzinfo=_BERLIN_IN_WINTER),
            datetime(year=2023, month=1, day=1, hour=6, tzinfo=_BERLIN_IN_WINTER),
            "2023-01-01 00:00 to 2023-01-01 06:00 UTC+01:00",
        ),
    ],
)
def test_a_period_names_its_start_and_its_end_and_the_zone_once(start: datetime, end: datetime, text: str) -> None:
    assert readable_period(start=start, end=end) == text
