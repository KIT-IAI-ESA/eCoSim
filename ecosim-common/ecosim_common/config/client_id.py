from dataclasses import dataclass


@dataclass(frozen=True)
class ClientID:
    model_name: str
    simulator_name: str

    def __str__(self) -> str:
        return f"{self.model_name}#{self.simulator_name}"

    def to_str(self) -> str:
        return self.__str__()
