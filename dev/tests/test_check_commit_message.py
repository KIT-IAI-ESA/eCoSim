import subprocess
from pathlib import Path

import pytest

from check_commit_message import find_errors, main


@pytest.mark.parametrize(
    "message",
    [
        "feat: add file based repository",
        "fix!: drop the old run options",
        "fix(parser): handle multiple spaces",
        "feat(server)!: drop the old api",
        "docs: describe the config\n\nCloses #12",
        "fix: Dask channel at shutdown",
        "test: add dask tests\n# a comment",
        "Merge pull request #3 from mekkyz/dask",
        'Revert "feat: add file based repository"',
    ],
)
def test_valid(message: str) -> None:
    assert find_errors(message) == []


@pytest.mark.parametrize(
    ("message", "error"),
    [
        ("TECH: move tests", "unknown type 'TECH'"),
        ("add x", "<type>: <summary>"),
        ("feat:add x", "<type>: <summary>"),
        ("feat(): add x", "<type>: <summary>"),
        ("fixup! feat: add x", "<type>: <summary>"),
        ("feat: add x\nmore", "blank line"),
        ("", "<type>: <summary>"),
    ],
)
def test_invalid(message: str, error: str) -> None:
    assert any(error in found for found in find_errors(message))


@pytest.mark.parametrize(("message", "exit_code"), [("feat: add x\n", 0), ("add x\n", 1)])
def test_main_with_file(tmp_path: Path, message: str, exit_code: int) -> None:
    file = tmp_path / "COMMIT_EDITMSG"
    file.write_text(message, encoding="utf-8")
    assert main([str(file)]) == exit_code


def test_main_with_revisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q"], check=True)
    for message in ["chore: add start", "feat: add x", "fixed y"]:
        subprocess.run([*git, "commit", "-q", "--allow-empty", "--no-verify", "-m", message], check=True)

    assert main(["--revisions", "HEAD~1", "^HEAD~2"]) == 0
    assert main(["--revisions", "HEAD~2..HEAD"]) == 1
    assert "fixed y" in capsys.readouterr().err
