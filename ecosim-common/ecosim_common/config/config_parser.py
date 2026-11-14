import configparser
import errno
import math
import os.path
import re
from argparse import ArgumentTypeError
from enum import Enum
from pathlib import Path
from typing import List

from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.logger.logger import ESPLogger


class ConfigParser:
    _logger = ESPLogger("ConfigParser")

    def __init__(
        self,
        path: Path,
    ):
        ConfigParser.ensure_file_exists(path)
        self.config_file: Path = path
        self._config: configparser.ConfigParser = configparser.ConfigParser(interpolation=None)
        try:
            self._config.read(path)
        except configparser.Error as error:
            raise ConfigParserException(self._unreadable_file_message(error=error)) from error

    def _unreadable_file_message(self, error: configparser.Error) -> str:
        # configparser shows the file as its repr, like PosixPath('...')
        if isinstance(error, configparser.DuplicateSectionError):
            return f"{self.config_file} has the section [{error.section}] twice, the second time in line {error.lineno}"
        if isinstance(error, configparser.MissingSectionHeaderError):
            return f"{self.config_file} has to start with a section like [server], not '{error.line.strip()}' in line {error.lineno}"
        if isinstance(error, configparser.ParsingError):
            first_line_number, _ = error.errors[0]
            return self._parsing_error_line(line_number=first_line_number)
        return f"{self.config_file} cannot be read: {error.message}"

    def _parsing_error_line(self, line_number: int) -> str:
        # Python 3.12 keeps only the repr of each line
        line = self.config_file.read_text(encoding="locale").splitlines()[line_number - 1]
        return f"{self.config_file}: line {line_number} has to be a section like [server] or a key = value, not '{line.strip()}'"

    def get_bool(
        self,
        section: str,
        option: str,
        default: bool | None = None,
    ) -> bool:
        try:
            value = self._get(section, option)
        except ConfigParserException as e:
            if default is not None:
                ConfigParser._logger.debug("Config '%s.%s' was not found. So the default value '%s' will be used.", section, option, default)
                return default
            raise e
        try:
            return self.config_string_to_bool(value)
        except ConfigParserException as error:
            raise ConfigParserException(f"{self.config_file}: {option} in [{section}] has to be true or false, not '{value}'") from error

    def get_string_array(
        self,
        section: str,
        option: str,
    ) -> List[str]:
        value = self._get(section, option)
        try:
            return self.config_string_to_string_array(value)
        except ConfigParserException as error:
            raise ConfigParserException(
                f"{self.config_file}: {option} in [{section}] has to be a list in brackets, like {option} = [{value}]",
            ) from error

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
                ConfigParser._logger.debug("Config '%s.%s' was not found. So the default value '%s' will be used.", section, option, default)
                return default
            raise e

    def get_enum[T: Enum](
        self,
        enum_class: type[T],
        section: str,
        option: str,
        default: T | None = None,
    ) -> T:
        try:
            value = self.get_string(section, option)
        except ConfigParserException as e:
            if default is not None:
                ConfigParser._logger.debug("Config '%s.%s' was not found. So the default value '%s' will be used.", section, option, default)
                return default
            raise e
        if value not in enum_class.__members__:
            message = f"{self.config_file}: {option} in [{section}] has to be one of {', '.join(enum_class.__members__)}, not '{value}'"
            hint = did_you_mean(name=value, known_names=enum_class.__members__)
            raise ConfigParserException(f"{message}.{hint}" if hint else message)
        return enum_class[value]

    def get_int(
        self,
        section: str,
        option: str,
    ) -> int:
        value = self._get(section, option)
        try:
            return int(value)
        except ValueError as e:
            raise ConfigParserException(f"{self.config_file}: {option} in [{section}] has to be a whole number, not '{value}'") from e

    def contains(
        self,
        section: str,
        option: str,
    ) -> bool:
        return self._config.has_option(section, option)

    def _get(
        self,
        section: str,
        option: str,
    ) -> str:
        try:
            return self._config.get(section, option)
        except configparser.NoSectionError as e:
            raise MissingSectionOrKeyException(f"{self.config_file} has no section [{section}]") from e
        except configparser.NoOptionError as e:
            raise MissingSectionOrKeyException(f"{self.config_file} has no key {option} in [{section}]") from e

    def extract_extra_sections(self) -> List[str]:
        return ConfigParser.extract_extra_sections_from_config_file(self.config_file)

    @staticmethod
    def extract_extra_sections_from_config_file(path: str | Path) -> List[str]:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return ConfigParser._extract_extra_sections_from_text(text)

    @staticmethod
    def _extract_extra_sections_from_text(text: str) -> List[str]:
        # Find all section headers like [SectionName]
        header_pattern = re.compile(r"^\s*\[(.+?)\]\s*$", re.MULTILINE)
        matches = list(header_pattern.finditer(text))
        if not matches:
            return []

        excluded = {"server", "simulator"}
        sections: list[str] = []
        for index, match in enumerate(matches):
            section_name = match.group(1).strip()
            if section_name.lower() in excluded:
                continue
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            sections.append(block)

        return sections

    @staticmethod
    def config_string_to_string_array(string: str | None) -> List[str]:
        if not string:
            return []
        match = re.match(r"\[(.*)\]", string)
        if match:
            return [item.strip().strip('"').strip("'") for item in match.group(1).split(",")]
        raise ConfigParserException(
            f"Input cannot be parsed to a string array: {string}",
        )

    @staticmethod
    def config_string_to_int_array(string: str) -> List[int]:
        return [int(item) for item in ConfigParser.config_string_to_string_array(string)]

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
    def config_bool_or_string_to_bool(value: bool | str) -> bool:
        if isinstance(value, bool):
            return value
        return ConfigParser.config_string_to_bool(value)

    @staticmethod
    def positive_whole_number(text: str) -> int:
        if not text.strip().isdecimal() or int(text) < 1:
            raise ArgumentTypeError(f"must be a whole number of at least 1, not '{text}'")
        return int(text)

    @staticmethod
    def port_number(text: str) -> int:
        if not text.strip().isdecimal() or not 1 <= int(text) <= 65535:
            raise ArgumentTypeError(f"must be a port number from 1 to 65535, not '{text}'")
        return int(text)

    @staticmethod
    def number_from_zero_to_one(text: str) -> float:
        try:
            number = float(text)
        except ValueError:
            # nan fails the range check below
            number = math.nan
        if not 0 <= number <= 1:
            raise ArgumentTypeError(f"must be a number from 0 to 1, not '{text}'")
        return number

    @staticmethod
    def true_or_false(text: str) -> bool:
        try:
            return ConfigParser.config_string_to_bool(text)
        except ConfigParserException:
            raise ArgumentTypeError(f"must be true or false, not '{text}'") from None

    @staticmethod
    def choice_name(text: str) -> str:
        return text.strip().lower().replace("-", "_")

    @staticmethod
    def ensure_file_exists(path: str | Path) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))


class ConfigParserException(Exception):
    def __init__(
        self,
        message: str | None,
    ) -> None:
        super().__init__(message)


class MissingSectionOrKeyException(ConfigParserException):
    pass
