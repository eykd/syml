---
name: pytest-unit-testing
description: 'Use when: (1) writing new unit tests for syml, (2) reviewing existing tests, (3) implementing TDD workflows, (4) creating fixtures/parametrized cases, (5) debugging test failures, (6) questions about test design. Covers pytest, mypy, and ruff conventions in this repo.'
---

# Python Unit Testing with pytest & TDD

This skill is the **pytest layer** over `/test-driven-development` — see that
skill for the TDD discipline itself (the Test List, Red-Green-Refactor, the
greening strategies, and the generic test references). This skill covers the
pytest/mypy/ruff conventions specific to `syml` and this project's **100%
branch-coverage mandate**.

## Core Decision: What Are You Testing?

| Scenario                         | Approach                                  |
| --------------------------------- | ------------------------------------------ |
| A pure function (`syml.loads`)    | Test directly, no mocks                    |
| A `SymlNode` subclass in isolation | Fresh instance per test, no shared state   |
| A grammar/parser behavior          | Drive it through `SymlParser.parse` or `syml.loads`, not internal visitor methods |
| A genuinely unreachable branch     | `# pragma: nocover` / `# pragma: nobranch`, sparingly (see below) |

`syml` has almost no I/O and no external dependencies to mock — most tests are
plain input → output assertions against `syml.loads`/`syml.load`, or against
`parsers.SymlParser().parse(...)` when a test needs the intermediate
`SymlNode` tree (`as_data()` / `as_source()`).

## File and Test Naming

- One test module per source module: `tests/test_<module>.py` mirrors
  `src/syml/<module>.py` (`tests/test_parsers.py` ↔ `src/syml/parsers.py`,
  `tests/test_nodes.py` ↔ `src/syml/nodes.py`).
- Group related tests in a class named after the unit under test:
  `class TestSymlParser:`, `class TestSimpleParserFunction:`. This is the
  established pattern in `tests/test_parsers.py` — follow it for new test
  modules rather than inventing a flat function-per-test style.
- Test method names read as a sentence: `test_it_should_parse_a_simple_text_value`,
  `test_it_fails_parsing_weird_indentations`. Start with `test_it_should_...`
  (or `test_it_...` for a negative/failure case) and describe the observable
  behavior, not the implementation path.

## Type Annotations Are Mandatory

mypy's `files` setting in `pyproject.toml` covers `tests/` as well as `src/`
and `tools/`, and `disallow_untyped_defs = true` applies repo-wide. Every test
function needs `-> None`, and every fixture needs a return type annotation:

```python
import pytest

from syml import parsers


class TestSymlParser:
    @pytest.fixture
    def parser(self) -> parsers.SymlParser:
        return parsers.SymlParser()

    def test_it_should_parse_a_simple_text_value(self, parser: parsers.SymlParser) -> None:
        result = parser.parse('true')
        assert result.as_data() == 'true'
```

`uv run mypy` (or `just type-check`) must pass with zero errors before
committing — there is no separate "tests are exempt" carve-out.

## `pytest.mark.parametrize` for Tables

Prefer `parametrize` over near-duplicate test methods whenever the only
difference between cases is the input/expected pair:

```python
import pytest

import syml


class TestLoads:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('foo: bar', {'foo': 'bar'}),
            ('- foo\n- bar\n', ['foo', 'bar']),
            ('just text', 'just text'),
        ],
    )
    def test_it_should_load_various_shapes(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected
```

Each parametrized case shows up as its own entry in `-vv` output (already in
`addopts`), so failures point straight at the failing input.

## `pytest.raises` with `match=`

Always assert on the exception message (or a stable substring of it) with
`match=`, not just the exception type — a bare `pytest.raises(SomeError)`
passes even if the wrong branch raised it:

```python
import pytest

from syml.exceptions import OutOfContextNodeError


class TestOutOfContextError:
    def test_it_should_raise_on_a_bad_dedent(self) -> None:
        text = '  - foo:\n      - bar\n - baz\n- blah\n'
        with pytest.raises(OutOfContextNodeError, match='line=3'):
            syml.loads(text)
```

`match` takes a regex searched against `str(exception)`, so escape any
regex metacharacters that appear in the literal text you're matching.

## Random Order Independence

`addopts` includes `--random-order` (via pytest-random-order), so tests run
in a different order every invocation. This means:

- No shared mutable module- or class-level state between tests
- No test that depends on another test having run first (e.g. relying on a
  side effect from a prior test's fixture)
- Fixtures are function-scoped by default here (`@pytest.fixture` with no
  `scope=`) — keep it that way unless you have a specific, documented reason
  for a broader scope, since broader scopes are exactly where order-dependent
  bugs creep in

If a test fails only under certain random seeds, that is a bug in the test's
isolation, not a flaky test to retry.

## `# pragma: nocover` / `# pragma: nobranch` Policy

The coverage gate (`--cov-fail-under=100`, branch coverage on) is enforced
only by pre-commit and CI — a green `uv run pytest` locally can still fail at
commit time. Before reaching for a pragma, ask: can this branch actually be
exercised by a test? Almost always yes.

Reserve `# pragma: nocover` / `# pragma: nobranch` for branches that are
**provably unreachable**, matching the established pattern in `nodes.py` and
`parsers.py`:

```python
# src/syml/nodes.py — an abstract method's default body, never actually
# executed because every concrete subclass overrides it
def as_data(self) -> Any:  # noqa: ANN401  # pragma: nocover
    """Render this node as plain data."""

# src/syml/parsers.py — an `else` branch that mirrors an `if` already proven
# exhaustive by the grammar, kept only for defensive clarity
else:  # pragma: nocover  # noqa: RET505
    ...
```

**Acceptable**: an abstract/overridden method body, a defensive `else` that
the grammar makes unreachable, a branch that only differs in whether a
condition variable is truthy in a way the type system or call sites already
rule out.

**Not acceptable**: skipping a branch because writing the test is
inconvenient, or because triggering an error path takes a slightly awkward
input. If a branch is reachable by *some* real SYML document or Python call,
write that test instead of pragma-ing it away.

## Running a Single Test File

```sh
uv run pytest tests/test_parsers.py::TestSymlParser::test_it_should_parse_a_simple_text_value --no-cov
```

`--no-cov` matters here: `addopts` turns on `--cov` project-wide, and a
single-file or single-test run will always report far under 100% (everything
else in `src/` looks "uncovered" from that one run's perspective) unless you
suppress it. Coverage numbers are only meaningful for a full `uv run pytest`
run — `just test-coverage` is what should read 100%, not a scoped one.

For the fast iterate-until-green loop use `./runtests.sh` (ruff fix + format,
then `pytest --exitfirst --failed-first --new-first`, then mypy) or
`./watchtests.sh` to rerun it on every `.py` save.

## TDD Red/Green/Refactor Cycle

This repo's outer loop (ralph / `/sp:*`) treats a RED commit as a distinct,
inspectable step:

1. **Red**: write a failing test first. If it exercises a not-yet-existing
   name, stub the implementation with `raise NotImplementedError` and a full
   type signature, so mypy and test collection both pass while the test
   itself still fails on the assertion:

   ```python
   def parse_something(text: str) -> dict[str, str]:
       """Parse a not-yet-implemented shape."""
       raise NotImplementedError
   ```

2. Confirm the test actually fails (`uv run pytest <path> --no-cov`), then
   record the RED commit: `.venv/bin/python -m tools.commit_red <task-id>`.
   This is a ralph-worker/`/sp:*` convention — it marks that a real failing
   test exists before implementation starts, so the outer loop can prove the
   test wasn't vacuous.
3. **Green**: write the minimum implementation to pass. Run `uv run pytest`
   (full suite, so coverage is meaningful) before moving on.
4. **Refactor**: with tests green, clean up duplication or naming under the
   safety net, re-running the suite after each change.

See `/test-driven-development` for the underlying discipline (Kent Beck's
test desiderata, the Test List, when to fake it vs. obvious implementation).

## ruff Conventions for Tests

`pyproject.toml`'s `[tool.ruff.lint.per-file-ignores]` already exempts
`tests/**/*.py` from:

- `S101` — `assert` is how pytest tests assert; the bandit rule against bare
  `assert` in production code doesn't apply here
- the `D100`-series docstring rules — no docstring requirement on test
  functions/classes (the test name is the documentation)
- `INP001` — test directories don't need `__init__.py` for ruff's
  implicit-namespace-package check
- `ARG001` — an unused fixture parameter (e.g. a fixture requested only for
  its side effect) is fine in a test

Everything else in the enabled rule set (imports via `I`, `SIM`, `RUF`,
`UP`, etc.) still applies to test files. Run `uv run ruff check --fix && uv
run ruff format` (or `just fix`) before committing; `runtests.sh` already
does this as its first step.

## References

- `references/examples.md` — Concrete, verified test examples against the
  real `syml` API (`syml.loads`, `OutOfContextNodeError`,
  `Source`/`Pos` from `syml.basetypes`)
- **acceptance-tests** skill — Gherkin/pytest-bdd layer above this one
- **test-driven-development** skill — generic TDD discipline (Test List,
  Red-Green-Refactor, greening strategies)
