import threading
from typing import Type, Any, TypeVar, cast

T = TypeVar('T', bound='Singleton')


# Attention: this will result in a deadlock if a singleton instantiate a non-initialized singleton in its init method
class Singleton(type):
    _instances: dict[type, Any] = {}
    _lock = threading.Lock()

    def __call__(
        cls: Type[T],  # type: ignore
        *args: Any,
        **kwargs: Any,
    ) -> T:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cast(T, cls._instances[cls])
