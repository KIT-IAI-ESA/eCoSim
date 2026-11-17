import textwrap
from dataclasses import dataclass

from ecosim_common.tech import banner
from ecosim_common.tech.deployment.module_version import get_module_version


@dataclass(frozen=True)
class ConsoleScript:
    name: str
    description: str
    examples: tuple[str, ...] = ()

    def version(self) -> str:
        return get_module_version(name=self.name)

    def examples_text(self) -> str | None:
        if not self.examples:
            return None
        return "\n".join(["examples:", *(textwrap.indent(text=example, prefix="  ") for example in self.examples)])

    def print_banner(self) -> None:
        banner.print_banner()
        # keeps the banner above the log lines from stderr in a log file
        print(f"{self.name} {self.version()}", flush=True)
