from collections import Counter
from typing import Any, Collection, Mapping

from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.readable_count import readable_count


def unknown_key_warnings_of_object(where: str, raw_object: Any, read_keys: Collection[str], accepted_keys: Collection[str] = ()) -> list[str]:
    if not isinstance(raw_object, dict):
        return []
    return [
        f'{where} has the unknown key "{key}".{did_you_mean(name=key, known_names=read_keys)}'
        for key in raw_object
        if key not in read_keys and key not in accepted_keys
    ]


def unknown_key_warnings_of_entries(
    where: str,
    noun: str,
    entries: Any,
    read_keys: Collection[str],
    accepted_keys: Collection[str] = (),
    hints: Mapping[str, str] | None = None,
) -> list[str]:
    if not isinstance(entries, list):
        return []
    counts = Counter(key for entry in entries if isinstance(entry, dict) for key in entry if key not in read_keys and key not in accepted_keys)
    return [
        f'{where}: {readable_count(count=count, noun=noun)} {"has" if count == 1 else "have"} the unknown key "{key}".'
        + did_you_mean(name=key, known_names=read_keys)
        + (f" {hints[key]}" if hints and key in hints else "")
        for key, count in counts.items()
    ]
