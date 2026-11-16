import io
from contextlib import redirect_stdout
from importlib.metadata import version

import pytest

from tests.config.console_script_test_setup import CONSOLE_SCRIPT


def test_the_banner_ends_with_the_name_and_the_version_of_the_command(capsys: pytest.CaptureFixture[str]) -> None:
    CONSOLE_SCRIPT.print_banner()

    assert capsys.readouterr().out.splitlines()[-1] == f"ecosim-common {version('ecosim-common')}"


def test_an_output_that_cannot_show_the_block_letters_still_gets_the_name_and_the_version() -> None:
    written = io.BytesIO()
    cp1252_output = io.TextIOWrapper(buffer=written, encoding="cp1252")

    with redirect_stdout(cp1252_output):
        CONSOLE_SCRIPT.print_banner()

    assert written.getvalue().decode("cp1252").splitlines() == ["eCoSim", f"ecosim-common {version('ecosim-common')}"]
