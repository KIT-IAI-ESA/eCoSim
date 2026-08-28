from types import MappingProxyType
from typing import List, Any


# by default, pydantic serialize to snake_case (instead to camelCase)
#    -> so this method is used to serialize to camelCase to be compliant with the current recommendation
#       of JSON
def to_camel_case(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def object_to_camel_case_dict(instance: Any) -> dict[Any, Any] | Any:
    return _object_to_camel_case_dict(vars(instance))


def _object_to_camel_case_dict(obj: Any) -> dict[Any, Any] | List[dict[Any, Any]] | MappingProxyType[str, Any] | Any:
    if not isinstance(obj, dict) and not hasattr(obj, "__dict__"):
        return obj
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_key = to_camel_case(k)  # Transform key to camelCase
            new_dict[new_key] = _object_to_camel_case_dict(v)  # Recursively apply to values
        return new_dict
    if isinstance(obj, list):
        return [_object_to_camel_case_dict(i) for i in obj]  # Apply transformation to list items
    return obj
