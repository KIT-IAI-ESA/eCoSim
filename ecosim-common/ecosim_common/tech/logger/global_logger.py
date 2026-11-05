from collections.abc import Collection
from typing import Any

from ecosim_common.tech.logger.logger import ESPLogger


class GlobalLogger:
    logger = ESPLogger("")
    _header_padding = 7
    _wall_thickness = 2
    _list_padding = 4

    @staticmethod
    def print_values(
        header: str,
        value_pairs: dict[str, Any],
        key_value_seperator: str = ":",
        list_point_character: str = "├",
    ) -> None:
        for line in GlobalLogger.format_values_to_lines(header, value_pairs, key_value_seperator, list_point_character):
            GlobalLogger.logger.info("%s", line)

    @staticmethod
    def format_values_to_lines(
        header: str,
        value_pairs: dict[str, Any],
        key_value_seperator: str = ":",
        list_point_character: str = "├",
    ) -> list[str]:
        header_bar = "#" * (len(header) + 2 * GlobalLogger._header_padding + 2 * GlobalLogger._wall_thickness)
        padding = " " * GlobalLogger._header_padding
        lines = [header_bar, f"{GlobalLogger._wall()}{padding}{header}{padding}{GlobalLogger._wall()}", header_bar]
        for key, value in value_pairs.items():
            lines.extend(GlobalLogger._format_value(key, value, key_value_seperator, list_point_character))
        return [*lines, header_bar]

    @staticmethod
    def _format_value(key: str, value: Any, key_value_seperator: str, list_point_character: str) -> list[str]:
        wall = GlobalLogger._wall()
        # strings are iterable so we explicitly need to check for strings
        if not isinstance(value, Collection) or isinstance(value, str):
            return [f"{wall} {key}{key_value_seperator} {value}"]
        list_padding = " " * GlobalLogger._list_padding
        return [f"{wall} {key}{key_value_seperator}", *(f"{wall}{list_padding}{list_point_character} {item}" for item in value)]

    @staticmethod
    def _wall() -> str:
        return "#" * GlobalLogger._wall_thickness
