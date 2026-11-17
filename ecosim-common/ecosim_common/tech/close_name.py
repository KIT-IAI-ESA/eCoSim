import difflib
from typing import Iterable


def closest_name(name: str, known_names: Iterable[str], cutoff: float = 0.75) -> str | None:
    names = list(known_names)
    same_but_for_case = [known_name for known_name in names if known_name.lower() == name.lower()]
    if same_but_for_case:
        return same_but_for_case[0]
    close_names = difflib.get_close_matches(word=name, possibilities=names, n=1, cutoff=cutoff)
    return close_names[0] if close_names else None


def did_you_mean(name: str, known_names: Iterable[str], cutoff: float = 0.75) -> str:
    closest = closest_name(name=name, known_names=known_names, cutoff=cutoff)
    return "" if closest is None else f" Did you mean {closest}?"
