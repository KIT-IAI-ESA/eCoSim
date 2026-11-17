from pathlib import Path

import pytest

import ecosim_common.config.config_parser as config_parser
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.config_parser import ConfigParser
from ecosim_test_common.resources.resource_utils import config_parser_for_resource


def test_config_parser() -> None:
    config = config_parser_for_resource("configs/config.ini")
    # SECTION 1
    assert config.get_string("Section1", "string") == "section1-string"
    assert config.get_string_array("Section1", "string_array") == ["section1-string-array-1", "section1-string-array-2"]
    assert config.get_bool("Section1", "boolean_true") is True
    assert config.get_bool("Section1", "boolean_yes") is True
    assert config.get_bool("Section1", "boolean_false") is False
    assert config.get_bool("Section1", "boolean_no") is False
    assert config.get_int("Section1", "int") == 1111
    # SECTION 2
    assert config.get_string("Section2", "string") == "section2-string"
    assert config.get_string_array("Section2", "string_array") == ["section2-string-array-1", "section2-string-array-2"]
    assert config.get_bool("Section2", "boolean_true") is True
    assert config.get_bool("Section2", "boolean_yes") is True
    assert config.get_bool("Section2", "boolean_false") is False
    assert config.get_bool("Section2", "boolean_no") is False
    assert config.get_int("Section2", "int") == 2222


def test_empty_string() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    assert config.get_string("Section1", "string_empty") == ""


def test_empty_string_array() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    assert config.get_string_array("Section1", "string_array_empty") == []


def test_empty_bool() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException):
        config.get_bool("Section1", "bool_empty")


def test_a_value_that_is_not_a_boolean_shows_the_key_and_the_value_also_with_a_default() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException) as error_info:
        config.get_bool(section="Section1", option="bool_invalid", default=False)
    assert str(error_info.value) == f"{config.config_file}: bool_invalid in [Section1] has to be true or false, not 'not parsable as bool'"


def test_a_missing_key_shows_the_file_the_section_and_the_key() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException) as error_info:
        config.get_string("Section1", "non_existing")
    assert str(error_info.value) == f"{config.config_file} has no key non_existing in [Section1]"


def test_non_existing_bool() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException):
        config.get_bool("Section1", "non_existing")


def test_non_existing_int() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException):
        config.get_int("Section1", "non_existing")


def test_a_value_that_is_not_a_whole_number_shows_the_key_and_the_value() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException) as error_info:
        config.get_int("Section1", "int_invalid")
    assert str(error_info.value) == f"{config.config_file}: int_invalid in [Section1] has to be a whole number, not 'asdfsad'"


def test_non_existing_string_array() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException):
        config.get_string_array("Section1", "non_existing")


def test_a_list_without_brackets_shows_how_to_write_it() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException) as error_info:
        config.get_string_array("Section1", "string_array_invalid")
    expected = f"{config.config_file}: string_array_invalid in [Section1] has to be a list in brackets, like string_array_invalid = [klasjdf]"
    assert str(error_info.value) == expected


def test_a_missing_section_shows_the_file_and_the_section() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    with pytest.raises(config_parser.ConfigParserException) as error_info:
        config.get_string_array("NON_EXISTING", "string_empty")
    assert str(error_info.value) == f"{config.config_file} has no section [NON_EXISTING]"


def test_an_unknown_enum_value_lists_the_known_values_and_the_close_one(tmp_path: Path) -> None:
    file = tmp_path / "preferences.ini"
    file.write_text("[server]\ncommunication_protocol = tcp_socket\n", encoding="utf-8")
    with pytest.raises(config_parser.ConfigParserException) as error_info:
        ConfigParser(file).get_enum(
            enum_class=CommunicationProtocol,
            section="server",
            option="communication_protocol",
            default=CommunicationProtocol.TCP_SOCKET,
        )
    expected = f"{file}: communication_protocol in [server] has to be one of DASK, TCP_SOCKET, not 'tcp_socket'. Did you mean TCP_SOCKET?"
    assert str(error_info.value) == expected


def test_a_missing_file_shows_its_path(tmp_path: Path) -> None:
    file = tmp_path / "preferencs.ini"
    with pytest.raises(FileNotFoundError) as error_info:
        ConfigParser(file)
    assert error_info.value.filename == str(file)


@pytest.mark.parametrize("content", ["[server]\nport 1234\nhost = localhost\n", "[server]\nport 1234\nhost localhost\n"])
def test_a_file_with_lines_that_are_not_a_key_or_a_section_shows_the_file_and_the_first_of_them(tmp_path: Path, content: str) -> None:
    file = tmp_path / "preferences.ini"
    file.write_text(content, encoding="utf-8")

    with pytest.raises(config_parser.ConfigParserException) as error_info:
        ConfigParser(file)

    assert str(error_info.value) == f"{file}: line 2 has to be a section like [server] or a key = value, not 'port 1234'"


def test_a_key_before_the_first_section_shows_the_file_and_the_line(tmp_path: Path) -> None:
    file = tmp_path / "preferences.ini"
    file.write_text("# the server\nport = 1234\n[server]\n", encoding="utf-8")

    with pytest.raises(config_parser.ConfigParserException) as error_info:
        ConfigParser(file)

    assert str(error_info.value) == f"{file} has to start with a section like [server], not 'port = 1234' in line 2"


def test_a_section_written_twice_shows_the_file_and_the_second_line(tmp_path: Path) -> None:
    file = tmp_path / "preferences.ini"
    file.write_text("[server]\nport = 1234\n[server]\nhost = localhost\n", encoding="utf-8")

    with pytest.raises(config_parser.ConfigParserException) as error_info:
        ConfigParser(file)

    assert str(error_info.value) == f"{file} has the section [server] twice, the second time in line 3"


def test_string_to_bool() -> None:
    assert config_parser.ConfigParser.config_string_to_bool("true") is True
    assert config_parser.ConfigParser.config_string_to_bool("True") is True
    assert config_parser.ConfigParser.config_string_to_bool("TRUE") is True
    assert config_parser.ConfigParser.config_string_to_bool("false") is False
    assert config_parser.ConfigParser.config_string_to_bool("False") is False
    assert config_parser.ConfigParser.config_string_to_bool("FALSE") is False
    assert config_parser.ConfigParser.config_string_to_bool("yes") is True
    assert config_parser.ConfigParser.config_string_to_bool("Yes") is True
    assert config_parser.ConfigParser.config_string_to_bool("YES") is True
    assert config_parser.ConfigParser.config_string_to_bool("no") is False
    assert config_parser.ConfigParser.config_string_to_bool("No") is False
    assert config_parser.ConfigParser.config_string_to_bool("NO") is False


def test_non_existing_string_with_default_value() -> None:
    config = config_parser_for_resource("configs/edge_cases.ini")
    default_value = "my_default_value"
    assert config.get_string("Section1", "non_existing", default_value) == default_value


def test_parse_string_array() -> None:
    string_array = '["hello", "world"]'
    actual = ConfigParser.config_string_to_string_array(string_array)
    assert actual[0] == "hello"
    assert actual[1] == "world"


def test_parse_string_array_none_array() -> None:
    actual = ConfigParser.config_string_to_string_array(None)
    assert len(actual) == 0


def test_parse_string_array_empty_string() -> None:
    actual = ConfigParser.config_string_to_string_array("")
    assert len(actual) == 0


def test_parse_string_array_without_quotes() -> None:
    actual = ConfigParser.config_string_to_string_array("[10, False, hello, 1.11]")
    assert actual == ["10", "False", "hello", "1.11"]


def test_parse_string_array_invalid_string() -> None:
    with pytest.raises(config_parser.ConfigParserException):
        ConfigParser.config_string_to_string_array("90,ajksaf")


def test_parse_int_array() -> None:
    string_array = "[888, 222]"
    actual = ConfigParser.config_string_to_int_array(string_array)
    assert actual[0] == 888
    assert actual[1] == 222


def test_extract_extra_sections() -> None:
    config = config_parser_for_resource("configs/common_client_config.ini")
    assert len(config.extract_extra_sections()) == 1
    assert config.extract_extra_sections()[0] == """[fmu]\nfmu_file=[/path/to/fmu.fmu]"""


def test_extract_multiple_sections() -> None:
    config = config_parser_for_resource("configs/config_multiple_sections.ini")
    assert len(config.extract_extra_sections()) == 2
    assert (
        config.extract_extra_sections()[0]
        == """[Section1]
string = string1234
int = 12"""
    )
    assert (
        config.extract_extra_sections()[1]
        == """[Section2]
string = string5678
int = 23"""
    )


def test_no_extra_sections() -> None:
    config = config_parser_for_resource("configs/config_no_extra_section.ini")
    assert config.extract_extra_sections() == []
