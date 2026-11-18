import json
from pathlib import Path
from typing import Any


def read_json_file(file: Path) -> dict[str, Any]:
    with open(file, encoding="utf-8") as opened_file:
        try:
            content = json.load(opened_file)
        except json.JSONDecodeError as error:
            raise ValueError(f"{file} is not valid JSON: {error.msg} in line {error.lineno}, column {error.colno}.") from error
        except UnicodeDecodeError as error:
            line = error.object[: error.start].count(b"\n") + 1
            raise ValueError(f"{file} is not saved as UTF-8: line {line} has a character in another encoding. Save the file as UTF-8.") from error
    if not isinstance(content, dict):
        raise ValueError(f"{file} has to contain a JSON object in {{ }}.")
    return content
