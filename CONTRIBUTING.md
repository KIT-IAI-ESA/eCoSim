# Contributing

Questions, bug reports and pull requests are welcome. Everyone taking part follows the
[code of conduct](CODE_OF_CONDUCT.md).

## Questions and bugs

Open an issue. For a bug, say what you ran (the command and the config files, or a small example),
what you expected and what happened, and add the log of the run with `--debug`. The
[documentation](https://ecosim.easimov.com/docs) covers many setup problems, so a quick look
there first often helps.

A security problem doesn't belong in a public issue, see [SECURITY.md](SECURITY.md).

## Pull requests

- for anything bigger than a small fix, open an issue first, so we can agree on the way before you
  spend time on it
- keep a pull request small and about one thing
- add or change the tests for what you changed, and update the docs when the behaviour changes
- run the checks before you push, see [Testing](docs/content/development/testing.md#before-a-commit)
- write the commit messages as [Conventional Commits](docs/content/development/developing.md), CI
  checks them

## Development setup

The development pages are in `docs/content/development/` and on the
[documentation site](https://ecosim.easimov.com/docs/development/project-setup).

- [Project setup](docs/content/development/project-setup.md): install uv, set up the environments and the pre-commit hook
- [Architecture](docs/content/development/architecture.md): the subprojects and how they work together
- [Coding guidelines](docs/content/development/coding-guidelines.md)
- [Development tips](docs/content/development/tips.md): what reviews look for
- [Testing](docs/content/development/testing.md): run the tests and the checks before a commit
- [Developing](docs/content/development/developing.md): commit messages and the documentation
- [Dependencies](docs/content/development/dependencies.md): add a dependency or bump the version
- [Adding a subproject](docs/content/development/adding-a-subproject.md)
