from ecosim_common.tech.singleton import Singleton


class TestSingleton(metaclass=Singleton):
    def __init__(self) -> None:
        self.my_string: str = "First init"


def test_singleton() -> None:
    singleton_1 = TestSingleton()
    assert singleton_1.my_string == "First init"
    singleton_1.my_string = "after init"
    assert singleton_1.my_string == "after init"
    assert TestSingleton().my_string == "after init"
