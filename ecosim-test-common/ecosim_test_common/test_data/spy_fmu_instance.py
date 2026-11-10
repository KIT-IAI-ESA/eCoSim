from dataclasses import dataclass, field


@dataclass
class SpyFMUInstance:
    """Acts like an fmpy FMU and records whether it was freed."""

    terminate_fails: bool = field(default=False)
    free_instance_fails: bool = field(default=False)
    is_freed: bool = field(default=False)

    def terminate(self) -> None:
        if self.terminate_fails:
            raise RuntimeError("terminate failed")

    def freeInstance(self) -> None:
        if self.free_instance_fails:
            raise RuntimeError("freeInstance failed")
        self.is_freed = True
