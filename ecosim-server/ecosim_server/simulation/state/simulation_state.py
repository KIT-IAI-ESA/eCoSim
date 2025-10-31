from enum import Enum


class SimulationState(Enum):
    NOT_READY = ("Not ready", "not ready")
    READY = ("Ready", "ready")
    STARTED = ("Started", "started")
    FAILED = ("Failed", "failed")
    FINISHED = ("Finished", "finished")

    def __new__(
        cls,
        display_value: str,
        db_entry: str,
    ):
        obj = object.__new__(cls)
        obj._value_ = display_value  # Set the value for the enum member
        obj.display_value = display_value
        obj.db_entry = db_entry
        return obj

    def __str__(self):
        # Custom string representation for the enum member
        return self.display_value

    @classmethod
    def of_db_entry(
        cls,
        db_entry: str,
    ):
        try:
            normalized_entry = db_entry.strip().lower()
            return next(member for member in cls if member.db_entry == normalized_entry)
        except StopIteration:
            raise ValueError(f"'{db_entry}' is not a valid SimulationState")
