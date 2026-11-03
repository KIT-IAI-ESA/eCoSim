# Coding guidelines

More conventions, with examples from the code: [Development tips](tips.md).

## Code

- concise, readable code that follows PEP 8 and the existing patterns
- type hints on every function signature and class attribute, including `-> None`; mypy runs with
  `disallow_untyped_defs`
- meaningful names, no abbreviations
- arguments passed by name, `repository.add(values=values, timestamp=timestamp)`, except for a
  single obvious argument such as `Path(file)`
- comments in English
- short, clear docstrings for complex logic
- composition over inheritance, early returns over nesting
- repeated logic goes into the class that owns it, otherwise into a helper function
- handle errors gracefully

## Size

- methods ≤ 10 lines, but don't extract only 2 lines into a new method
- classes ≤ 150 lines, but don't create a class for ≤ 10 lines
- files ≤ 150 lines; split large modules into focused ones

## Tests

- test-driven: write the test first
- pytest, with high coverage

## Enforced by pre-commit

- Python filenames in `snake_case` (`dev/validate_file_name.py`)
- lines of at most 150 characters (`ruff`, `flake8`, `.editorconfig`)
- a trailing comma in multi-line calls and signatures, added by `add-trailing-comma`
- a newline at the end of every file
- no leftover `breakpoint()` or `pdb`
- no file larger than 4 MB (`check-added-large-files`)
- no f-strings in log calls (ruff `G004`): `logger.debug("x %s", value)`
- no access to private members of other objects (ruff `SLF001`)
- shell scripts pass `shellcheck`
- `pyproject.toml` files pass `validate-pyproject`, which also rejects unknown classifiers

Run it before every commit, see [Testing](testing.md#before-a-commit).
