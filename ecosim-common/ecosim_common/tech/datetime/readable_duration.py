def readable_duration(seconds: float) -> str:
    if round(seconds, 2) < 1:
        return f"{seconds:.2f} s"
    if round(seconds, 1) < 10:
        return f"{seconds:.1f} s"
    if round(seconds) < 600:
        return _in_two_units(amounts=divmod(round(seconds), 60), units=("min", "s"))
    return _in_two_units(amounts=divmod(round(seconds / 60), 60), units=("h", "min"))


def _in_two_units(amounts: tuple[int, int], units: tuple[str, str]) -> str:
    return " ".join(f"{amount} {unit}" for amount, unit in zip(amounts, units, strict=True) if amount > 0)
