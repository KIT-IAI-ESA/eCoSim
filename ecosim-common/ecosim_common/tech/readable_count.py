def readable_count(count: int, noun: str) -> str:
    """Like '1 step' or '2,523 steps'."""
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"
