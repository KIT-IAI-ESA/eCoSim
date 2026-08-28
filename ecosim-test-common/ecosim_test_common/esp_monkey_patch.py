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

    def remove_pytest_sys_args(self) -> None:
        self.monkey_patch.setattr(sys, "argv", ["ecosim"])

    def set_hpc_cli_sys_args(
        self,
        simulator_dir: str = "/path/to/simulator",
        simulation_config_file: str = "/path/to/simulation_config_file",
        server_config_file: str = "/path/to/server_config_file",
        steps: str = "100",
        port: str = "22222",
    ) -> None:
        self.set_sys_arg("--simulator-dir", simulator_dir)
        self.set_sys_arg("--simulation-config", simulation_config_file)
        self.set_sys_arg("--server-config", server_config_file)
        self.set_sys_arg("--steps", steps)
        self.set_sys_arg("--port", port)


@pytest.fixture
def esp_monkey_patch(monkeypatch: pytest.MonkeyPatch) -> ESPMonkeyPatch:
    return ESPMonkeyPatch(monkeypatch)
