# by default, pydantic serialize to snake_case (instead to camelCase)
#    -> so this method is used to serialize to camelCase to be compliant with the current recommendation
#       of JSON
def to_camel_case(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])
