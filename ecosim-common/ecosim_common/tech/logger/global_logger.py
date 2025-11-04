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
        header_length = len(header) + 2 * GlobalLogger._header_padding + 2 * GlobalLogger._wall_thickness
        header_bar = "#" * header_length
        wall = "#" * GlobalLogger._wall_thickness
        list_padding = " " * GlobalLogger._list_padding
        GlobalLogger.logger.info(header_bar)
        GlobalLogger.logger.info(f"{wall}{' ' * GlobalLogger._header_padding}{header}{' ' * GlobalLogger._header_padding}{wall}")
        GlobalLogger.logger.info(header_bar)
        for key, value in value_pairs.items():
            # strings are iterable so we explicitly need to check for strings
            if not isinstance(value, Collection) or isinstance(value, str):
                GlobalLogger.logger.info(f"{wall} {key}{key_value_seperator} {value}")
            else:
                GlobalLogger.logger.info(f"{wall} {key}{key_value_seperator}")
                for item in value:
                    GlobalLogger.logger.info(f"{wall}{list_padding}{list_point_character} {item}")
        GlobalLogger.logger.info(header_bar)
