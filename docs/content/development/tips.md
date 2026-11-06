# Development tips

We look for these in reviews, on top of the [coding guidelines](coding-guidelines.md) and the [testing](testing.md) page.

These points also serve as instructions for coding assistants, so they go into more detail than a person needs. For
day-to-day work, the main points are enough.

## Names

- Stick to the words the code already uses, like `listener` and `connector`; made-up ones are harder to follow.
- Drop words from a name that don't match the code, like `step` on a delay or `copy` on a test that copies nothing.
- Name a side effect nobody would expect: `__pop_and_notify` rather than `__notify`, since it also removes the listener.
- Give related names one pattern, like `<Behaviour>ShutdownListener`. A long name is fine if it shows the intent.

## Comments and log messages

- Use comments to say why, as in `# add before checking, so a shutdown starting right now cannot miss it`.
- Delete (or rewrite) comments that repeat the code or only made sense for an older version of it.
- Update comments and log messages along with the code, or they'll mislead the next person who debugs with them.

## Tests

Name a test after what it guarantees, not the steps it takes, and make sure the assert fails when that behaviour
breaks. For an important feature, check the result, not only that no error came up.

```python
# test_signal_while_the_shutdown_sets_the_event_is_ignored
# before: holds whether or not the signal is ignored
assert listener.notification_count == 1
# after: fails if the signal reaches sys.exit
assert exit_codes == []
```

- Assert only what the test is about: match the client id in an error message, and skip asserts on side effects.
- Check state on the object or a test double; asserts on log output with `caplog` are the exception.
- Give behaviour that other tests rely on its own test, such as the order in which listeners are notified.
- Skip tests of unimportant details, of odd cases whose cause is fixed for good, and of pytest and its plugins
  themselves. Lots of small tests like these make refactoring harder and add maintenance and review time.
- Keep what a test depends on visible: pass a timeout to a helper as an argument, so the call shows it.
- Add a type annotation where it lets mypy catch a regression, such as a value that must not become `None` again.

## Test doubles and helpers

We write test doubles as `@dataclass` subclasses of the real interface, with fields that record what happened.
When an assert fails, pytest prints those fields, and mypy checks every override:

```python
@dataclass
class RaisingShutdownListener(ShutdownListener):
    notified: bool = field(default=False)

    @override
    def on_app_shutdown(self) -> None:
        self.notified = True
        raise RuntimeError("listener failed")
```

- Put test doubles in a shared module, like `ecosim-common/tests/tech/shutdown_listeners.py`, and code that builds
  common test objects in a shared place such as `ecosim_test_common/test_data/`, so other tests can reuse them.
- Integration-test setups that other tests can use belong in `SimpleTestServer` or `SimpleTestClient`.
- Name a fixture after what it does. If every test needs it, make it `autouse` with a docstring saying what it's for.
- Please use `monkeypatch` sparingly. It patches by name, so tests break easily and an IDE rename misses it.
  Pass things in, like a timeout as a constructor parameter that defaults to the old value.
- If tests need to skip part of a setup method, keep calling the method and give it a parameter that switches that
  part off, so code added to it later still runs in tests.

## Constants

- In tests, reference production constants like `ShutdownManager.TERMINATE_EXIT_CODE`, so the value can change
  without touching the test.
- Keep a constant that is used in one place inline or as a local variable.
- Constants that many tests share, like a wait timeout, go in a common module such as `ecosim_test_common/timeouts.py`.

## Fixing the cause

- If you find a bug in code you're refactoring, fix it in the same change, while the code is open and under test.
- Fix structural problems in the production code. A workaround in a test leaves production with the problem.
- Wait for a completion signal where there is one; a sleep only guesses how long the work takes.

## Changes

- When you can't tell what an approach might break, go with the less invasive one.
- If a fix turns into a bigger behaviour change, open an issue so we can discuss it first.
- Run the [performance tests](testing.md#performance-tests) before merging a change that may cost performance,
  such as one in the main loop, so we can measure instead of guessing.
- Remove code that looks unused in a pull request, so the review can spot an unfinished concept. If something
  still needs it, a test should break.
- Legacy code that's too costly to refactor can go once its hard-to-produce expected data is kept in
  `ecosim_test_common/resources/` and a test with a real model uses it (see [Simulations](testing.md#simulations)).
- Update the docs in the same pull request as the behaviour they describe.
