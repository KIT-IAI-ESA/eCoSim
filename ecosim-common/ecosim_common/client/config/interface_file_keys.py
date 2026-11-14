"""The keys of an .fmc file that the clients read."""

from collections import Counter
from pathlib import Path
from typing import Any

from ecosim_common.tech.json.unknown_json_keys import unknown_key_warnings_of_entries, unknown_key_warnings_of_object

KINDS = (("inputs", "input"), ("outputs", "output"))


def unknown_key_warnings(raw_interfaces: Any, fmc_file: Path) -> list[str]:
    # the .fmc files of the examples have fmu-file and modeldescription, and the docs say that nothing reads them
    warnings = unknown_key_warnings_of_object(
        where=str(fmc_file),
        raw_object=raw_interfaces,
        read_keys=("inputs", "outputs"),
        accepted_keys=("fmu-file", "modeldescription"),
    )
    if not isinstance(raw_interfaces, dict):
        return warnings
    for kind, noun in KINDS:
        warnings += unknown_key_warnings_of_entries(
            where=str(fmc_file),
            noun=noun,
            entries=raw_interfaces.get(kind),
            read_keys=("name", "unit", "description", "required"),
            accepted_keys=("type", "connected_to"),
        )
    return warnings


def repeated_name_warnings(raw_interfaces: Any, fmc_file: Path) -> list[str]:
    if not isinstance(raw_interfaces, dict):
        return []
    return [
        f"{fmc_file} lists the {noun} {name} {count} times."
        for kind, noun in KINDS
        for name, count in Counter(_names_of(entries=raw_interfaces.get(kind))).items()
        if count > 1
    ]


def _names_of(entries: Any) -> list[str]:
    return [entry["name"] for entry in entries if isinstance(entry, dict) and entry.get("name")] if isinstance(entries, list) else []
