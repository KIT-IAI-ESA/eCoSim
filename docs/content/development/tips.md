# Development tips

Conventions for code and tests that come up in reviews, beyond
[Coding guidelines](coding-guidelines.md). How to run the tests is in [Testing](testing.md).

## Names

- a name says what the code does, side effects included: `__pop_and_notify`, because nobody
  expects a method called `__notify` to remove the listener
- the code base's own words are reused: the ends of a channel are `listener` and `connector`, not
  a new "waiting side", since a made-up word has the reader look for a difference that is not there
- related names follow one pattern, as the listener doubles do with `<Behaviour>ShutdownListener`;
  a long one such as `GraceEndingSignalRaisingShutdownListener` is fine when it shows the intention
- fixtures are named after what they do, such as `auto_initialize_shutdown_manager` rather than
  `signal_handlers`, since an autouse fixture never appears in the tests it runs for

## Comments and log messages

- a comment states the intention, not the mechanics, which the code already shows:
  `# add before checking, so a shutdown starting right now cannot miss it` keeps the next reader
  from swapping the two statements below it and bringing the race back
- comments that repeat the code are deleted, such as "must be implemented by the subclass" on an
  `@abstractmethod`, which already says so
- comments that only make sense next to the previous version of the code are deleted too, since the
  reader sees only the current one
- when the code changes, its comments and log messages change with it: once the reset was gone,
  `"All listeners notified - resetting ShutdownManager itself."` became `"All listeners notified."`,
  because a log line about something that no longer happens misleads whoever debugs with it

## Tests

- the name states what the test guarantees, not the steps it takes, so a failure says which
  guarantee broke: `test_signal_does_not_deadlock_while_the_interrupted_code_holds_the_lock`, not
  `test_signal_exits_while_the_interrupted_code_holds_the_lock`
- names that point the wrong way are fixed too: `..._does_not_raise` read as if the listener must
  not raise, so it became `test_exception_of_a_listener_registered_after_shutdown_is_caught`
- behaviour that other tests or code rely on gets its own test: several shutdown tests depend on the
  order of notification, so `test_listeners_are_notified_in_the_order_of_registration` pins it
- complex tests get the short docstring the [coding guidelines](coding-guidelines.md#code) ask for,
  written for whoever reads the test after it fails
- what a test depends on is visible in its body, or in a double whose name says what it does:
  implicit behaviour makes a test hard to follow and lets it fail on refactorings that change
  nothing it checks. When only a hook reaches the moment under test, the hook sits in the test
  body with a docstring, as in `test_shutdown_starting_while_a_listener_registers_notifies_it_once`
- pytest and its plugins are not tested here, such as whether the timeout plugin fails a hanging
  test: they have their own tests, and a check that a shared fixture is used would have to be
  repeated in every subproject
- fragile tests with side effects beyond their subject, such as one that patches
  `distributed.Queue.get` for every queue, are deleted when another test covers the same behaviour

### What a test asserts

An assert has to fail when the behaviour in the title breaks. In the first version of
`test_signal_while_the_shutdown_sets_the_event_is_ignored`, the assert held either way, and a
signal that got through showed only as a `SystemExit` the test did not check:

```python
# before: notification_count is 1 whether or not the signal is ignored
assert listener.notification_count == 1
# after: exit_codes records the calls of sys.exit
assert exit_codes == []
```

A test checks state, not log output: the wording of a log line changes while the behaviour stays the
same. A double records that it was reached, and the object under test shows the result in its
fields. `caplog` is for a log line that is itself the behaviour, as in
`test_failed_tcp_connection_names_the_transport_and_the_address`. When private state is the only
place the result shows, a test may read it despite the
[SLF001 rule](coding-guidelines.md#enforced-by-pre-commit), marked with `# noqa: SLF001`:

```python
# before: depends on the wording of the log line
assert "Shutdown listener RaisingShutdownListener failed" in caplog.text
# after: the double was reached, and the manager dropped it
assert raising_listener.notified
assert id(raising_listener) not in ShutdownManager._listener  # noqa: SLF001
```

## Test doubles and shared test code

Doubles are `@dataclass` subclasses of the real interface. They record what happened in fields
(`notified`, `finished`, `notification_count`, `calls`) for the test to assert on. pytest prints
those fields when an assert fails, and mypy checks each override against the interface:

```python
@dataclass
class RaisingShutdownListener(ShutdownListener):
    notified: bool = field(default=False)

    @override
    def on_app_shutdown(self) -> None:
        self.notified = True
        raise RuntimeError("listener failed")
```

- doubles go into the shared module of their kind, such as
  `ecosim-common/tests/tech/shutdown_listeners.py`, rather than into the test that first needs
  them, so the next test reuses them
- creation logic for common objects lives in `ecosim_test_common/test_data/`, such as
  `generate_unused_connection_address()`, so no test writes its own

## Constants

- tests use the production constant instead of repeating its value, such as
  `ShutdownManager.TERMINATE_EXIT_CODE` or `binary_message_header.HEADER_BYTES - 1`: the value then
  changes without touching the test, and a boundary case stays on the boundary
- a constant used at one place is written inline or as a local variable, since a module-level name
  sends the reader looking for other uses
- test-wide constants, such as a wait timeout, go into a common module in `ecosim_test_common`, so
  the import does not tie a test to the helper that happened to need them first
- exit codes stay below 256, because POSIX keeps only the lowest 8 bits: 444 arrives as 188

## Fixing the cause

- bugs found in code under refactoring, such as the `_init` flag of `ShutdownManager` that was
  never set, are fixed in the same change, while the code is open and under test anyway
- a structural problem is fixed in the production code, since a workaround in a test leaves
  production with it. For a lost Dask scheduler, a `DaskChannel.close()` that logs a warning and
  goes on is enough for now; a fixture that resets the `ShutdownManager` would only hide the problem
- components close only what they created, because a shared resource such as the Dask client may
  still be needed by other shutdown listeners
- a sleep that guesses how long the work takes gives way to a completion signal where one is
  possible, such as all shutdown listeners having run

## Changes and tooling

- of two approaches whose consequences are hard to estimate, the less invasive one is chosen, since
  less can go wrong with it
- a change that may cost performance, such as a timeout on a socket that accepts in a loop, waits
  for the automated performance test, so a regression shows in numbers instead of being guessed
- code that looks unused is removed in a pull request: if it was still used, a test breaks, and the
  review can spot a concept that is not finished yet
- legacy code too costly to refactor can be removed once its hard-to-produce expected data is in
  `ecosim_test_common/resources/` and a test of a real model takes its place, as the house
  simulation under [Simulations](testing.md#simulations) shows
- the docs change in the same pull request as the behaviour they describe, so `main` never
  documents behaviour it no longer has
- recurring developer tasks are Python scripts in `dev/`, so every task starts the same way whatever
  runs underneath; `dev/build_docs.py` can build in Docker, so nobody installs npm just for the docs
