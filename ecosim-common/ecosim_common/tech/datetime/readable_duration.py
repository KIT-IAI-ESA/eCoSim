def readable_duration(seconds: float) -> str:
    """Like '0.04 s', '4.2 s', '42 s', '3 min 26 s', '12 min' or '2 h 5 min'."""
    if round(seconds, 2) < 1:
        return f"{seconds:.2f} s"
    if round(seconds, 1) < 10:
        return f"{seconds:.1f} s"
    # from 10 minutes on, the seconds do not matter
    if round(seconds) < 600:
        return _in_two_units(amounts=divmod(round(seconds), 60), units=("min", "s"))
    return _in_two_units(amounts=divmod(round(seconds / 60), 60), units=("h", "min"))


def _in_two_units(amounts: tuple[int, int], units: tuple[str, str]) -> str:
    return " ".join(f"{amount} {unit}" for amount, unit in zip(amounts, units, strict=True) if amount > 0)
