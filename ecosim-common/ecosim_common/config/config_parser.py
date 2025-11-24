import configparser
import os.path
import re
from pathlib import Path
from typing import List

from ecosim_common.tech.logger.logger import ESPLogger


class ConfigParser:
    _logger = ESPLogger("ConfigParser")

    def __init__(
        self,
        path: Path,
    ):
        ConfigParser.ensure_file_exists(path)
        self.config_file: Path = path
        self._config: configparser.ConfigParser = configparser.ConfigParser()
        self._config.read(path)

    def get_bool(
        self,
        section: str,
        option: str,
        default: bool | None = None,
    ) -> bool:
        try:
            return self.config_string_to_bool(self._get(section, option))
        except ConfigParserException as e:
            if default is not None:
                ConfigParser._logger.debug(
                    f"Config '{section}.{option}' was not found. So the default value '{default}' will be used.",
                )
                return default
            raise e

    def get_string_array(
        self,
        section: str,
        option: str,
    ) -> List[str]:
        return self.config_string_to_string_array(self._get(section, option))

    def get_string(
        self,
        section: str,
        option: str,
        default: str | None = None,
    ) -> str:
        try:
            return self._get(section, option)
        except ConfigParserException as e:
            if default is not None:
                ConfigParser._logger.debug(
                    f"Config '{section}.{option}' was not found. So the default value '{default}' will be used.",
                )
                return default
            raise e

    def get_int(
        self,
        section: str,
        option: str,
    ) -> int:
        try:
            return int(self._get(section, option))
        except ValueError as e:
            raise ConfigParserException(
                f"Cannot parse value as int ({section}#{option})",
            ) from e

    def contains(
        self,
        section: str,
        option: str,
    ) -> int:
        return self._config.has_option(section, option)

    def _get(
        self,
        section: str,
        option: str,
    ) -> str:
        try:
            return self._config.get(section, option)
        except configparser.NoSectionError as e:
            raise ConfigParserException(f"The section {section} does not exist") from e
        except configparser.NoOptionError as e:
            raise ConfigParserException(
                f"In section {section} the key {option} does not exist",
            ) from e

    def extract_last_section(self) -> str:
        return ConfigParser.extract_last_section_from_config_file(self.config_file)

    @staticmethod
    def extract_last_section_from_config_file(path: str | Path) -> str:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        return ConfigParser._extract_last_section_from_text(text)

    @staticmethod
    def _extract_last_section_from_text(text: str) -> str:
        pattern = re.compile(r'^\s*\[.+?\]\s*$', re.MULTILINE)
        matches = list(pattern.finditer(text))
        if not matches:
            raise ValueError("Config enthält keine Sektionen.")
        start = matches[-1].start()
        return text[start:].strip()

    @staticmethod
    def config_string_to_string_array(string: str | None) -> List[str]:
        if not string:
            return []
        match = re.match(r"\[(.*)\]", string)
        if match:
            return [
                item.strip().strip('"').strip("'") for item in match.group(1).split(",")
            ]
        raise ConfigParserException(
            f"Input cannot be parsed to a string array: {string}",
        )

    @staticmethod
    def config_string_to_int_array(string: str) -> List[int]:
        return [
            int(item) for item in ConfigParser.config_string_to_string_array(string)
        ]

    @staticmethod
    def config_string_to_bool(string: str) -> bool:
        if not string:
            raise ConfigParserException("Input is empty")
        string_lower_case = string.strip().lower()
        if string_lower_case in ["true", "yes"]:
            return True
        elif string_lower_case in ["false", "no"]:
            return False
        else:
            raise ConfigParserException(f"Can not parse {string} to bool")

    @staticmethod
    def ensure_file_exists(path: str | Path) -> None:
        if not os.path.exists(path):
            raise Exception(
                f"Cannot open path: {path}. Current working directory: {os.getcwd()}",
            )


class ConfigParserException(Exception):
    def __init__(
        self,
        message: str | None,
    ) -> None:
        super().__init__(message)
