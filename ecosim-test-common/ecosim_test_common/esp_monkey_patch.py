from __future__ import annotations

import sys
from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class ESPMonkeyPatch:
    monkey_patch: pytest.MonkeyPatch

    def _strip(self, args: list[str], arg: str) -> list[str]:
        out, i = [], 0
        while i < len(args):
            if args[i] == arg:
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    i += 1
            elif args[i].startswith(f"{arg}="):
                i += 1
            else:
                out.append(args[i])
                i += 1
        return out

    def set_sys_arg(self, new_arg: str, *value: str) -> None:
        args = self._strip(sys.argv.copy(), new_arg)
        args.extend([new_arg, *value])
        self.monkey_patch.setattr(sys, "argv", args)

    def unset_sys_arg(self, arg: str) -> None:
        self.monkey_patch.setattr(sys, "argv", self._strip(sys.argv.copy(), arg))


@pytest.fixture
def esp_monkey_patch(monkeypatch: pytest.MonkeyPatch) -> ESPMonkeyPatch:
    return ESPMonkeyPatch(monkeypatch)
