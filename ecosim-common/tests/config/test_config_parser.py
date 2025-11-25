import pytest

import ecosim_common.config.config_parser as config_parser
from ecosim_common.config.config_parser import ConfigParser
from tests.tech.resource_utils import config_parser_for_resource


def test_config_parser() -> None:
    config = config_parser_for_resource('config.ini')
    # SECTION 1
    assert config.get_string('Section1', 'string') == 'section1-string'
    assert config.get_string_array('Section1', 'string_array') == ['section1-string-array-1', 'section1-string-array-2']
    assert config.get_bool('Section1', 'boolean_true') is True
    assert config.get_bool('Section1', 'boolean_yes') is True
    assert config.get_bool('Section1', 'boolean_false') is False
    assert config.get_bool('Section1', 'boolean_no') is False
    assert config.get_int('Section1', 'int') == 1111
    # SECTION 2
    assert config.get_string('Section2', 'string') == 'section2-string'
    assert config.get_string_array('Section2', 'string_array') == ['section2-string-array-1', 'section2-string-array-2']
    assert config.get_bool('Section2', 'boolean_true') is True
    assert config.get_bool('Section2', 'boolean_yes') is True
    assert config.get_bool('Section2', 'boolean_false') is False
    assert config.get_bool('Section2', 'boolean_no') is False
    assert config.get_int('Section2', 'int') == 2222


def test_empty_string() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    assert config.get_string('Section1', 'string_empty') == ''


def test_empty_string_array() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    assert config.get_string_array('Section1', 'string_array_empty') == []


def test_empty_bool() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_bool('Section1', 'bool_empty')


def test_invalid_bool() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_bool('Section1', 'bool_invalid')


def test_non_existing_string() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_string('Section1', 'non_existing')


def test_non_existing_bool() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_bool('Section1', 'non_existing')


def test_non_existing_int() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_int('Section1', 'non_existing')


def test_invalid_int() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_int('Section1', 'int_invalid')


def test_non_existing_string_array() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_string_array('Section1', 'non_existing')


def test_invalid_string_array() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_string_array('Section1', 'string_array_invalid')


def test_non_existing_section() -> None:
    config = config_parser_for_resource('edge_cases.ini')
    with pytest.raises(config_parser.ConfigParserException):
        config.get_string_array('NON_EXISTING', 'string_empty')


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
    config = config_parser_for_resource('edge_cases.ini')
    default_value = 'my_default_value'
    assert config.get_string('Section1', 'non_existing', default_value) == default_value


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
    assert actual == ['10', 'False', 'hello', '1.11']


def test_parse_string_array_invalid_string() -> None:
    with pytest.raises(config_parser.ConfigParserException):
        ConfigParser.config_string_to_string_array("90,ajksaf")


def test_parse_int_array() -> None:
    string_array = '[888, 222]'
    actual = ConfigParser.config_string_to_int_array(string_array)
    assert actual[0] == 888
    assert actual[1] == 222


def test_extract_sections_not_server_and_simulator() -> None:
    config = config_parser_for_resource('client_config.ini')
    assert len(config.extract_other_sections()) == 1
    assert config.extract_other_sections()[0] == """[fmu]\nfmu_file=[/path/to/fmu.fmu]"""


def test_extract_multiple_sections() -> None:
    config = config_parser_for_resource('config.ini')
    assert len(config.extract_other_sections()) == 2


def test_no_extra_sections() -> None:
    config_text = """
[server]
port=1234
[simulator]
name=test12
    """
    assert ConfigParser._extract_sections_from_text(config_text) == []
