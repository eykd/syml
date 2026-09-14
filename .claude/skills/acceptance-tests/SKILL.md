---
name: acceptance-tests
description: >
  Writing Gherkin acceptance specs and binding them with pytest-bdd.
  Use when creating new specs in specs/acceptance-specs/, binding a scenario's
  steps into tests/acceptance/, or troubleshooting the acceptance pipeline.
triggers:
  - write spec
  - write acceptance test
  - bind acceptance test
  - Gherkin spec
  - pytest-bdd
  - acceptance stub
  - spec writing
---

# Acceptance Tests Skill

## Decision Tree

```
What do you need?
│
├─ Write a new spec file
│  → Section: Writing Gherkin Specs (below)
│  → Reference: references/gwt-writing-guide.md
│
├─ Bind a scenario's steps into a real test
│  → Section: Binding Steps (below)
│  → Reference: references/binding-patterns.md
│
├─ Run the acceptance pipeline
│  → Section: Pipeline Quick Reference (below)
│
└─ Understand the TDD cycle around acceptance tests
   → Skill: pytest-unit-testing (inner Red-Green-Refactor loop)
   → Skill: test-driven-development (generic TDD discipline)
```

## Writing Gherkin Specs

Specs live in `specs/acceptance-specs/` as Gherkin `.feature` files. `bdd_features_base_dir = "specs/acceptance-specs"` is set in pyproject, so a binding's `scenarios("US<NN>-<slug>.feature")` call resolves relative to that directory — pass just the filename, not the full path.

### File Naming

```
specs/acceptance-specs/US<NN>-<kebab-case-title>.feature
```

One file per user story. The `US<NN>` prefix must match the story number used in beads. `specs/acceptance-specs/US00-smoke.feature` is the committed reference example — read it and its binding (`tests/acceptance/test_us00_smoke.py`) before writing a new one.

### Format

```gherkin
Feature: Short name for the user story
  A one- or two-sentence narrative: who wants this and why.

  Scenario: Description of the scenario
    Given some precondition
    When an action occurs
    Then an observable outcome

  Scenario Outline: Description with variation
    Given a document containing "<input>"
    When it is parsed
    Then the result is "<expected>"

    Examples:
      | input       | expected    |
      | name: syml  | name: syml  |
```

- `Feature:` line plus narrative, then one or more `Scenario:` blocks
- Steps use `Given`/`When`/`Then`, with `And`/`But` to continue a step's kind
- `Scenario Outline:` plus an `Examples:` table parameterizes a scenario over several rows
- No trailing periods required (unlike the old GWT `.txt` format) — write natural Gherkin sentences
- Multiple scenarios per feature file are allowed and encouraged: cover the happy path, edge cases, and error cases as separate scenarios in the same file

### Domain Language Discipline

Specs describe **what a SYML document contains and what parsing produces**, never how the parser is implemented internally.

**Good** — domain language:

```gherkin
Scenario: A nested list is parsed in document order
  Given a SYML document with a nested list
  When it is parsed
  Then the list items are returned in document order

Scenario: A badly dedented line fails to parse
  Given a document whose second line is indented deeper than any open container
  When it is parsed
  Then parsing fails with an out-of-context error naming line 2
```

**Bad** — implementation leakage:

```gherkin
Scenario: Parsimonious visits the mapping node
  Given a Parsimonious grammar rule matches a KeyValue node
  When SymlParser.visit_lines is called
  Then a ContainerNode.incorporate_node call succeeds
```

Rules:

- No code identifiers (class names, function names, module paths)
- No grammar/parser internals (Parsimonious, PEG, `NodeVisitor`, `ContainerNode`, `TextLeafNode`, `incorporate_node`)
- No Python exception class names in step text — describe the failure in domain terms ("parsing fails with an out-of-context error naming line 2"), and let the binding assert on the concrete exception type
- Talk about the SYML document (mappings, lists, keys, values, indentation, multiline values) and what `syml.loads`/`syml.load` return or raise — never about how the grammar gets there

See `references/gwt-writing-guide.md` for detailed examples and a review checklist.

## Binding Steps

### Architecture

```
specs/acceptance-specs/US<NN>-<slug>.feature  →  scenarios()  →  tests/acceptance/test_us<nn>_<slug>.py
```

Unlike a codegen pipeline, pytest-bdd binds directly: a binding module calls `scenarios("US<NN>-<slug>.feature")` and defines `@given`/`@when`/`@then` step functions matching the feature's step text. There is no generated-stub file to edit — you write the binding module yourself, following the shape of `tests/acceptance/test_us00_smoke.py`.

### Binding Module Shape

```python
"""Bindings for specs/acceptance-specs/US01-nested-lists.feature."""

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml

pytestmark = pytest.mark.acceptance

scenarios('US01-nested-lists.feature')


@given(parsers.parse('a SYML document containing "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    context['text'] = text


@when('it is parsed')
def when_parsed(context: dict[str, Any]) -> None:
    context['result'] = syml.loads(context['text'])


@then(parsers.parse('the result is a mapping with key "{key}" and value "{value}"'))
def then_mapping(context: dict[str, Any], key: str, value: str) -> None:
    assert context['result'] == {key: value}
```

Key points:

- `pytestmark = pytest.mark.acceptance` — required so `just acceptance`'s `-m acceptance` selects the module
- `scenarios('US<NN>-<slug>.feature')` — binds every scenario in that feature file to this module; the path resolves against `bdd_features_base_dir`
- The `context: dict[str, Any]` fixture (from `tests/acceptance/conftest.py`) carries state from `Given` to `When` to `Then` within one scenario
- `parsers.parse(...)` extracts `{placeholders}` from step text into function arguments — see `references/binding-patterns.md` for `parsers.re`, `parsers.cfparse`, and `target_fixture`
- Step functions need `-> None` and typed parameters like every other test function in this repo (mypy covers `tests/`)

See `references/binding-patterns.md` for parser choices, `target_fixture`, shared steps, Scenario Outline examples, tables, and error assertions.

## Pipeline Quick Reference

| Action                                  | Command                    |
| ---------------------------------------- | -------------------------- |
| Run the acceptance suite                 | `just acceptance`          |
| List every unbound step as a stub        | `just acceptance-missing`  |
| Unit + acceptance                        | `just test-all`            |

`just acceptance` runs `uv run pytest tests/acceptance -m acceptance --no-cov -o addopts="" -p no:random_order`. The unit run (`uv run pytest` / `just test`) both deselects `-m "not acceptance"` and `--ignore`s `tests/acceptance`, so acceptance scenarios only ever run through `just acceptance`.

**RED marker**: a scenario with no matching step function fails with `pytest_bdd.exceptions.StepDefinitionNotFoundError`. That is the acceptance-test equivalent of a failing test in Red-Green-Refactor — write the feature file first, watch it fail with `StepDefinitionNotFoundError`, then write the binding to go green.

`just acceptance-missing` runs pytest-bdd with `--generate-missing --feature specs/acceptance-specs` and prints ready-to-paste `@given`/`@when`/`@then` stubs for every step that has no binding yet. It exits 100 when steps are missing (hence `|| true` in the recipe) — use its output as a starting point, then fill in real assertions per `references/binding-patterns.md`.

## References

- `references/gwt-writing-guide.md` — Detailed Gherkin writing craft, good/bad examples, review checklist
- `references/binding-patterns.md` — Code templates for pytest-bdd step bindings
- **pytest-unit-testing** skill — pytest conventions, TDD micro loop, coverage policy
- **test-driven-development** skill — generic TDD discipline (Test List, Red-Green-Refactor)
