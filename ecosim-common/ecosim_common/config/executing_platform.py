from __future__ import annotations

import sys
from enum import Enum
from functools import cache


class ExecutingPlatform(Enum):
    """
    Identifies the executing platform. Use this enum for all platform-dependent
    code, so that all such code is easy to find.
    """

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    BSD = "bsd"
    CYGWIN = "cygwin"  # Windows host, POSIX semantics

    @staticmethod
    @cache
    def current() -> ExecutingPlatform:
        p = sys.platform
        if p == "win32":
            return ExecutingPlatform.WINDOWS
        if p.startswith("linux"):
            return ExecutingPlatform.LINUX
        if p == "darwin":
            return ExecutingPlatform.MACOS
        if p.startswith(("freebsd", "openbsd", "netbsd", "dragonfly")):
            return ExecutingPlatform.BSD
        if p in ("cygwin", "msys"):
            return ExecutingPlatform.CYGWIN
        raise Exception(f"Unsupported platform: {p}")

    @property
    def is_posix(self) -> bool:
        return self is not ExecutingPlatform.WINDOWS
