# Binding Patterns (pytest-bdd)

## Architecture

```
specs/acceptance-specs/US<NN>-<slug>.feature  →  scenarios()  →  tests/acceptance/test_us<nn>_<slug>.py
```

`bdd_features_base_dir = "specs/acceptance-specs"` (pyproject) means `scenarios("US<NN>-<slug>.feature")` resolves against that directory, not the binding module's own location. There is no codegen step: write the `.feature` file, then write the binding module by hand, following `tests/acceptance/test_us00_smoke.py` as the reference shape.

### Feature → Binding Workflow

1. Write the `.feature` file in `specs/acceptance-specs/`.
2. Run `just acceptance` — every scenario fails with `pytest_bdd.exceptions.StepDefinitionNotFoundError` (RED).
3. Run `just acceptance-missing` to print ready-to-paste `@given`/`@when`/`@then` stubs for the unbound steps.
4. Create `tests/acceptance/test_us<nn>_<slug>.py`: `pytestmark = pytest.mark.acceptance`, `scenarios('US<NN>-<slug>.feature')`, then fill in the stubs with real step functions.
5. Run `just acceptance` again until green.

## The `context` Fixture

`tests/acceptance/conftest.py` defines:

```python
@pytest.fixture
def context() -> dict[str, Any]:
    """Mutable scratch space carried between Given/When/Then steps of one scenario."""
    return {}
```

Every step function that needs to read or write state across steps takes `context: dict[str, Any]` as a parameter. It is fresh per scenario (function-scoped), so scenarios never leak state into each other.

## `parsers.parse` vs `parsers.re` vs `parsers.cfparse`

`parsers.parse` (Python's `string.Formatter`-based, from the `parse` library) is the default — use it unless a step needs something it can't express:

```python
@given(parsers.parse('a SYML document containing "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    context['text'] = text
```

`parsers.cfparse` adds type converters (`{count:d}`) via `parse_type` and is worth reaching for once a step needs a typed number rather than a string:

```python
from pytest_bdd import parsers

@then(parsers.cfparse('the result has {count:d} items'))
def then_item_count(context: dict[str, Any], count: int) -> None:
    assert len(context['result']) == count
```

`parsers.re` gives full regex control — reach for it only when `{placeholder}` matching in `parse`/`cfparse` can't express the step (e.g. matching one of several literal alternatives):

```python
from pytest_bdd import parsers

@then(parsers.re(r'the result is (?P<outcome>a mapping|a list|a string)'))
def then_outcome_kind(context: dict[str, Any], outcome: str) -> None:
    assert outcome in {'a mapping', 'a list', 'a string'}
```

Prefer `parsers.parse` first, `parsers.cfparse` when you need a converter, `parsers.re` last.

## `target_fixture`: Passing a Value from Given to When

`target_fixture` binds a step function's return value to a named fixture other steps can request directly, instead of stuffing it into `context` by hand:

```python
@given(parsers.parse('a SYML document containing "{text}"'), target_fixture='document_text')
def given_document(text: str) -> str:
    return text


@when('it is parsed', target_fixture='parse_result')
def when_parsed(document_text: str) -> Any:
    return syml.loads(document_text)


@then(parsers.parse('the result is a mapping with key "{key}" and value "{value}"'))
def then_mapping(parse_result: Any, key: str, value: str) -> None:
    assert parse_result == {key: value}
```

Use `context` for scenarios with several loosely related pieces of state; use `target_fixture` when a single value flows cleanly from one step to the next and naming it as a fixture reads better than a `context[...]` lookup.

## Shared Steps via `conftest.py`

A step used by more than one feature belongs in `tests/acceptance/conftest.py` (or a module imported by every binding that needs it) rather than copy-pasted per binding module — pytest-bdd discovers `@given`/`@when`/`@then` functions from any module that pytest collects fixtures from, so a shared step defined in `conftest.py` is visible to every binding in that directory tree.

```python
# tests/acceptance/conftest.py
from pytest_bdd import given, parsers


@given(parsers.parse('a SYML document containing "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    context['text'] = text
```

Keep a step in its own binding module until a second feature needs the exact same wording — premature sharing produces a `conftest.py` that's hard to trace back to any one scenario.

## Scenario Outline / `Examples:`

```gherkin
Scenario Outline: A simple mapping round-trips through the parser
  Given a SYML document containing "<line>"
  When it is parsed
  Then the result is a mapping with key "<key>" and value "<value>"

  Examples:
    | line         | key   | value |
    | name: syml   | name  | syml  |
    | color: blue  | color | blue  |
```

pytest-bdd expands each `Examples:` row into its own scenario at collection time — no special binding code is needed as long as the step text's `<placeholders>` line up with the `{placeholders}` your `@given`/`@when`/`@then` functions already parse. Each row shows up as a separate test in `just acceptance` output.

## Tables via `datatable`

A step followed by a Gherkin data table (not an `Examples:` table) receives it through the `datatable` fixture pytest-bdd injects:

```gherkin
Scenario: A mapping with several keys preserves all of them
  Given a SYML document with the following key-value pairs:
    | key   | value |
    | name  | syml  |
    | color | blue  |
  When it is parsed
  Then the result contains all of the given keys and values
```

```python
@given('a SYML document with the following key-value pairs:')
def given_document_from_table(context: dict[str, Any], datatable: list[list[str]]) -> None:
    header, *rows = datatable
    lines = [f'{key}: {value}' for key, value in rows]
    context['text'] = '\n'.join(lines)
```

`datatable` arrives as a list of rows (each a list of cell strings); the first row is the header.

## Error Assertions with `pytest.raises`

Capture the raised exception into `context` inside the `When` step so a later `Then` step can assert on it — never let the exception escape the step function uncaught, or the scenario fails at the wrong point with a less useful traceback:

```python
@when('it is parsed')
def when_parsed(context: dict[str, Any]) -> None:
    try:
        context['result'] = syml.loads(context['text'])
    except syml.exceptions.ParseError as exc:
        context['error'] = exc


@then(parsers.parse('parsing fails with an out-of-context error naming line {line:d}'))
def then_out_of_context_error(context: dict[str, Any], line: int) -> None:
    error = context['error']
    assert isinstance(error, syml.exceptions.OutOfContextNodeError)
    assert f'line={line}' in str(error)
```

Alternatively, when the `Then` step is the only place that needs to observe the failure, wrap the call itself in `pytest.raises` inside that step — this only works if `When` and `Then` are collapsed into one step, which is uncommon in Gherkin but valid:

```python
@then(parsers.parse('parsing "{text}" fails with a parse error'))
def then_parsing_fails(text: str) -> None:
    with pytest.raises(syml.exceptions.ParseError):
        syml.loads(text)
```

Prefer the first form (capture in `When`, assert in `Then`) — it keeps each step doing one Gherkin-shaped thing and matches how the rest of this repo's acceptance specs read.
