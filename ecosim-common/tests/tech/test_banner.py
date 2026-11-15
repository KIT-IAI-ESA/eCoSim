import contextlib
import io

import pytest
from ecosim_common.tech.banner import WORDMARK, print_banner


def test_the_banner_draws_the_wordmark_without_colour_codes_when_the_output_is_no_terminal(capsys: pytest.CaptureFixture[str]) -> None:
    print_banner()

    output = capsys.readouterr().out
    assert output.splitlines() == [f"{e}{rest}".rstrip() for e, rest in WORDMARK]
    assert "\x1b[" not in output


def test_a_console_that_cannot_show_block_characters_gets_the_name_in_letters() -> None:
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="\n")

    with contextlib.redirect_stdout(console):
        print_banner()

    assert console.buffer.getvalue().decode("cp1252") == "eCoSim\n"
