from ecosim_common.tech.close_name import closest_name, did_you_mean


def test_a_misspelled_name_gets_the_closest_known_name() -> None:
    assert closest_name(name="weatherBus_TDryBull", known_names=["weatherBus_TDryBul", "weatherBus_HDirNor"]) == "weatherBus_TDryBul"


def test_a_name_that_differs_only_in_case_comes_before_a_close_name() -> None:
    assert closest_name(name="HOUSE", known_names=["hose", "house"]) == "house"


def test_a_name_far_from_every_known_name_gets_none() -> None:
    assert closest_name(name="frobnicate", known_names=["house", "weather"]) is None


def test_did_you_mean_is_a_sentence_for_the_end_of_a_message_or_nothing() -> None:
    assert did_you_mean(name="hous", known_names=["house", "weather"]) == " Did you mean house?"
    assert did_you_mean(name="frobnicate", known_names=["house", "weather"]) == ""
