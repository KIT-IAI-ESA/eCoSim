from dataclasses import dataclass, field


@dataclass
class SpyFMUInstance:
    """Acts like an instantiated fmpy FMU and records whether it was freed."""

    terminate_fails: bool = field(default=False)
    is_freed: bool = field(default=False)
    # fmpy sets this handle on 'instantiate'
    component: object = field(default_factory=object)

    def terminate(self) -> None:
        if self.terminate_fails:
            raise RuntimeError("terminate failed")

    def freeInstance(self) -> None:
        self.is_freed = True
