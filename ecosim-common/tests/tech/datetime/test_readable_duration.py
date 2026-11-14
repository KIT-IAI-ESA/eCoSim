import pytest

from ecosim_common.tech.datetime.readable_duration import readable_duration


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0.043, "0.04 s"),
        (0.63, "0.63 s"),
        (4.24, "4.2 s"),
        (9.94, "9.9 s"),
        (9.96, "10 s"),
        (42.4, "42 s"),
        (59.6, "1 min"),
        (206, "3 min 26 s"),
        (599.6, "10 min"),
        (731, "12 min"),
        (900, "15 min"),
        (3_600, "1 h"),
        (7_512, "2 h 5 min"),
        (185_000, "51 h 23 min"),
    ],
)
def test_a_duration_reads_as_precise_as_its_size_needs(seconds: float, text: str) -> None:
    assert readable_duration(seconds) == text
