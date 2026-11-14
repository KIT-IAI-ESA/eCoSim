import pytest

from ecosim_common.tech.readable_count import readable_count


@pytest.mark.parametrize(("count", "text"), [(0, "0 steps"), (1, "1 step"), (2, "2 steps"), (2_523, "2,523 steps")])
def test_a_count_has_its_noun_in_the_singular_only_for_one(count: int, text: str) -> None:
    assert readable_count(count=count, noun="step") == text
