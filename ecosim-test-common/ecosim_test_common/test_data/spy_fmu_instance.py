from dataclasses import dataclass, field


@dataclass
class SpyFMUInstance:
    """Acts like an fmpy FMU of FMI 2.0 or 3.0 and records whether it was freed and the calls that start it."""

    terminate_fails: bool = field(default=False)
    free_instance_fails: bool = field(default=False)
    is_freed: bool = field(default=False)
    start_calls: list[str] = field(default_factory=list)

    def instantiate(self) -> None:
        self.start_calls.append("instantiate")

    def setupExperiment(self, startTime: float = 0.0) -> None:
        self.start_calls.append("setupExperiment")

    def setReal(self, valueReferences: list[int], values: list[float]) -> None:
        self.start_calls.append(f"setReal {valueReferences} {values}")

    def setFloat64(self, valueReferences: list[int], values: list[float]) -> None:
        self.start_calls.append(f"setFloat64 {valueReferences} {values}")

    # FMI 3.0 passes the start time here, FMI 2.0 to setupExperiment
    def enterInitializationMode(self, startTime: float = 0.0) -> None:
        self.start_calls.append("enterInitializationMode")

    def exitInitializationMode(self) -> None:
        self.start_calls.append("exitInitializationMode")

    def terminate(self) -> None:
        if self.terminate_fails:
            raise RuntimeError("terminate failed")

    def freeInstance(self) -> None:
        if self.free_instance_fails:
            raise RuntimeError("freeInstance failed")
        self.is_freed = True
