import os
import sys

# the eCoSim wordmark of the eASiMOV site in half blocks, each line split into the green e and the rest
WORDMARK = (
    ("              ", "     ▄▄▄▄▄▄▄▄                    ▄▄▄▄▄▄▄    ▄▄▄"),
    ("              ", "  ▄███▀▀▀▀▀███                ▄███▀▀▀▀███▄  ███"),
    ("     ▄▄▄▄▄▄   ", "  ███       ▀      ▄▄▄▄▄▄     ███      ▀▀   ▄▄▄  ▄▄▄ ▄▄▄▄▄  ▄▄▄▄▄"),
    ("  ▄███▀▀▀▀███▄", "  ███           ▄███▀▀▀▀███▄  ▀███▄▄▄▄▄     ███  ████████████████▄"),
    (" ███▄▄▄▄▄▄███ ", "  ███           ███      ███    ▀███████▄   ███  ███    ███    ███"),
    (" ███▀▀▀▀▀▀▀▀▀ ", "  ███           ███      ███          ▀███  ███  ███    ███    ███"),
    (" ███▄    ▄▄▄  ", "  ███▄     ▄█▄  ███▄    ▄███  ▄██▄    ▄███  ███  ███    ███    ███"),
    (" ▀▀██████▀▀   ", "   ▀▀████████▀   ▀▀██████▀▀    ▀███████▀▀   ███  ███    ███    ███"),
)


def print_banner() -> None:
    # the old Windows console prints colour codes as text, Windows Terminal sets WT_SESSION
    colour = sys.stdout.isatty() and "NO_COLOR" not in os.environ and (os.name != "nt" or "WT_SESSION" in os.environ)
    green, reset = ("\x1b[38;5;29m", "\x1b[0m") if colour else ("", "")
    try:
        print("\n".join(f"{green}{e}{reset}{rest}".rstrip() for e, rest in WORDMARK), flush=True)
    except UnicodeEncodeError:
        print("eCoSim", flush=True)
