import sys


def overwrite_system_argument(flag: str, value: str) -> None:
    argv = sys.argv
    # update if already present
    for i in range(1, len(argv)):
        if argv[i] == flag:
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                argv[i + 1] = value
            else:
                argv.insert(i + 1, value)
            return
        if argv[i].startswith(flag + "="):
            argv[i] = f"{flag}={value}"
            return
    # add if absent
    argv += [flag, value]
