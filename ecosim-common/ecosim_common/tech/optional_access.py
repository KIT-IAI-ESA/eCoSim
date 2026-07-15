"""
This class is a wrapper for access properties of objects that may be null.
So you can simply do

if_exists(my_object).its_property or my_alternative

instead of

my_object.its_property if my_object else my_alternative

"""

from typing import TypeVar, Generic, Any

T = TypeVar("T")


class OptionalAccess(Generic[T]):
    def __init__(
        self,
        obj: T,
    ) -> None:
        self.obj = obj

    def __getattr__(
        self,
        name: str,
    ) -> Any:
        if self.obj is None:
            return None
        return getattr(self.obj, name, None)

    def __or__(
        self,
        default: T,
    ) -> T:
        return self.obj or default


def if_exists(obj: T | None) -> T:
    """
    The return type is obviously not correct. Since all calls are delegated to the internal object it will work.
    So with the wrong return type, we get correct auto-completion and type checking.
    """
    return OptionalAccess(obj)  # type: ignore
