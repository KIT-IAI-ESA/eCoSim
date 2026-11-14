import textwrap
from dataclasses import dataclass

from ecosim_common.tech.deployment.module_version import get_module_version


@dataclass(frozen=True)
class ConsoleScript:
    """A command as its --help and its --version show it. The name is also the name of its package."""

    name: str
    description: str
    examples: tuple[str, ...] = ()

    def version(self) -> str:
        return get_module_version(name=self.name)

    def examples_text(self) -> str | None:
        if not self.examples:
            return None
        return "\n".join(["examples:", *(textwrap.indent(text=example, prefix="  ") for example in self.examples)])
