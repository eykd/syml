# Beads Task Description Templates

Parameterized templates for each task type. Replace `<placeholder>` variables with actual values when creating tasks.

## Type A Templates

### WRITE_ACCEPTANCE_TEST

```
**Type**: WRITE_ACCEPTANCE_TEST
**Story**: US<N> — <story title>
**Spec**: specs/$BRANCH/spec.md §US-<N>
**Acceptance scenarios**:
  1. GIVEN <precondition> WHEN <action> THEN <outcome>
  2. ...
**Feature file**: specs/acceptance-specs/US<N>-<kebab-title>.feature
**Bindings file**: tests/acceptance/test_us<n>_<kebab-title>.py
**Skills**: /pytest-unit-testing
**Instructions**: Write the Gherkin `.feature` file in `specs/acceptance-specs/`, then run `just acceptance-missing` to print stub step definitions for the unbound steps. Add the stub bindings to `tests/acceptance/test_us<n>_<kebab-title>.py`, marked `acceptance`, but leave the scenario unbound or the steps unimplemented so it FAILS (RED = `StepDefinitionNotFoundError` from `just acceptance`, or an assertion failure once bound to real behavior).
**Done when**: Feature file exists, bindings file exists, `just acceptance` shows the scenario failing.
**Commit**: Run `/sp-commit` then `git push`. Acceptance tests are `--ignore`d by the unit `uv run pytest` run and excluded from the coverage gate, so pre-commit passes. CI on the feature branch will fail until the implementation lands in subsequent tasks — that's expected. After closing the bead, commit and push again to record the beads state change.
```

Placeholders:

- `<N>`: User story number
- `<story title>`: From spec.md
- `$BRANCH`: Current git branch name
- `<precondition>`, `<action>`, `<outcome>`: From spec acceptance scenarios
- `<kebab-title>`: Kebab-case slug of story title
- `<n>`: Lowercase story number (matches the `test_us<n>_<slug>.py` naming convention)

### RED

```
**Type**: RED (write failing test)
**Story**: US<N> — <story title>
**Behavior**: <precise description of the single behavior to test>
**Spec**: specs/$BRANCH/spec.md §US-<N>
**Plan**: specs/$BRANCH/plan.md §<relevant-section>
**Test file**: <exact path, e.g. tests/test_nodes.py>
**Target module**: <exact path to the module being tested, e.g. src/syml/nodes.py>
**Existing patterns**: <reference to similar existing test files for style consistency>
**Layer CLAUDE.md**: <path to layer-specific instructions, if any>
**Skills**: /pytest-unit-testing
**Instructions**: This leaf is one Test List entry (see `/test-driven-development` → Test List). Write ONE failing test for this behavior. Import from the target module (create the module with just the type/function signature if it doesn't exist yet). The test must fail because the implementation doesn't exist or is incomplete, NOT because of import/syntax errors.
**Done when**: Test file exists, `uv run pytest <test-file> --no-cov` fails with an assertion error (not a collection/import error).
**Commit**: Stage the failing test (`git add <test-file>`), then run `.venv/bin/python -m tools.commit_red <task-id>`. It confirms the test fails, runs ruff/mypy/uv-lock (the `pytest-check` hook is skipped via `SKIP=pytest-check`), commits the failing test locally with `[skip ci]`, and does NOT push. Then `br close`. Do NOT push — the next Green task's push carries this commit as a non-tip ancestor.
```

Placeholders:

- `<behavior>`: One specific behavior being tested. Keep the phrase concise (≤ ~78 chars): the RED self-commit derives its `test: red — <behavior> [skip ci]` header from the title, and an over-long title is refused by `commit_red` rather than truncated.
- `<relevant-section>`: Section anchor in plan.md
- `<exact path>`: Full file path from repo root
- `<existing patterns>`: Path to a similar test file for style reference

### GREEN

```
**Type**: GREEN (minimal implementation)
**Story**: US<N> — <story title>
**Behavior**: <same behavior description as Red>
**Spec**: specs/$BRANCH/spec.md §US-<N>
**Plan**: specs/$BRANCH/plan.md §<relevant-section>
**Test file**: <exact test file path from Red task>
**Implementation files**: <exact paths to create/modify>
**Dependencies**: <imports, types, or interfaces this implementation needs>
**Layer CLAUDE.md**: <path to layer-specific instructions, if any>
**Skills**: <skill list from mapping table, e.g. /parsing>
**Instructions**: This leaf is one Test List entry (see `/test-driven-development` → Test List). Write the MINIMAL code to make the failing test pass (Obvious Implementation / Fake It / Triangulate). Do not add code beyond what the test requires. Do not refactor yet.
**Done when**: `uv run pytest <test-file> --no-cov` passes.
**Commit**: After tests pass, run `/sp-commit` then `git push` (this push also lands the preceding local RED commit, with the green tip on top). Then `br close`. After closing the bead, commit and push again to record the beads state change.
```

Placeholders:

- `<implementation files>`: Exact paths to create or modify
- `<dependencies>`: Imports, types, or interfaces needed
- `<skill list>`: From sp-05-tasks skill mapping table

### REFACTOR

```
**Type**: REFACTOR (improve quality)
**Story**: US<N> — <story title>
**Behavior**: <same behavior description>
**Test file**: <exact test file path>
**Implementation files**: <exact paths>
**Layer CLAUDE.md**: <path to layer-specific instructions, if any>
**Skills**: /refactoring
**Instructions**: Improve code quality (naming, duplication, clarity) without changing behavior. Run tests after each change to ensure they still pass. Skip if the code is already clean.
**Done when**: `uv run pytest <test-file> --no-cov` still passes, code meets quality standards (`uv run ruff check`, `uv run mypy` clean).
**Commit**: After tests pass, run `/sp-commit` then `git push`. After closing the bead, commit and push again to record the beads state change. Skip the first commit if no refactoring changes were made.
```

### VERIFY_ACCEPTANCE

```
**Type**: VERIFY_ACCEPTANCE
**Story**: US<N> — <story title>
**Feature file**: specs/acceptance-specs/US<N>-<kebab-title>.feature
**Bindings file**: tests/acceptance/test_us<n>_<kebab-title>.py
**Skills**: /pytest-unit-testing
**Instructions**: Run `just acceptance` for this story's scenario. If it passes (GREEN), close this task. If it fails — including `StepDefinitionNotFoundError` for any still-unbound step — diagnose which scenarios fail and add a comment explaining what's missing. Do NOT write new unit tests or implementation code — that work should be captured as new beads tasks if needed. **Completeness check before closing**: are there open discovered sub-tasks under this US story, or listed edge/error variants from the Test List with no leaf? If so, this story is NOT done — file them via `br create` and report incomplete. Do NOT write tests or code here (Verify stays assertion-only / no-commit so its HEAD-advance exemption holds).
**Done when**: `just acceptance` passes for this story's scenario.
**Commit**: After acceptance tests pass, run `/sp-commit` then `git push` (skip if no changes were made). After closing the bead, commit and push again to record the beads state change.
```

## Type B Template

### SPEC_PAGE

```
**Type**: SPEC_PAGE
**Story**: US<N> — <story title>
**Spec**: specs/$BRANCH/spec.md §US-<N>
**Plan**: specs/$BRANCH/plan.md §<relevant-section>
**Page file**: <exact path, e.g. SYML-SPECIFICATION.md, todo.txt, SYML-SPEC-REVIEW.md>
**Related files**: <other spec/doc pages or design-decision records involved>
**Instructions**: <what to write/change and why>
**Done when**: Content is accurate, internally consistent, and cross-references (e.g. `todo.txt` entries citing `SYML-SPEC-REVIEW.md` decisions) resolve correctly.
**Commit**: After verification passes, run `/sp-commit` then `git push`. After closing the bead, commit and push again to record the beads state change.
```

Placeholders:

- `<page file>`: Exact path to the spec/doc page
- `<related files>`: Other spec/doc pages or design-decision records involved

## Type D Template

### DOCUMENTATION

```
**Type**: DOCUMENTATION
**Files**: <exact paths>
**Instructions**: <what to document and why>
**Done when**: File exists with correct content. No broken links or formatting issues.
**Commit**: After verification passes, run `/sp-commit` then `git push`. After closing the bead, commit and push again to record the beads state change.
```

## Type E Template

### CONFIGURATION

```
**Type**: CONFIGURATION
**Files**: <exact paths, e.g. pyproject.toml, .pre-commit-config.yaml, justfile>
**Instructions**: <what to configure and why>
**Validation command**: <e.g. just check, uv run pytest, pre-commit run --all-files>
**Done when**: Validation command exits 0.
**Commit**: After verification passes, run `/sp-commit` then `git push`. After closing the bead, commit and push again to record the beads state change.
```

## Type F Template

### REMEDIATION

```
**Type**: REMEDIATION
**Review**: <review type — security, architecture, or quality>
**Finding**: <one-sentence problem description>
**File**: <exact path>
**Line**: <line number or range>
**Severity**: <Critical|High|Medium|Low>
**Fix**: <concise description of the required fix>
**Skills**: <relevant skills for this fix>
**Instructions**: <detailed fix instructions including what to change and why>
**Done when**: Fix applied, tests pass (`uv run pytest` or `just check`).
**Commit**: After verification passes, run `/sp-commit` then `git push`. After closing the bead, commit and push again to record the beads state change.
```

Placeholders:

- `<review type>`: One of: security, architecture, quality
- `<finding>`: From the review comment's problem column
- `<fix>`: From the review comment's fix column
- `<severity>`: Maps to priority (Critical→0, High→1, Medium→2, Low→3)
