---
name: beads-task-chains
description: Construct dependency chains for beads tasks based on work type (A-F). Use when creating structured task hierarchies for ATDD/TDD, spec/docs pages, config, or review remediations.
---

# Beads Task Chain Patterns

Reusable chain construction patterns for beads tasks. Consumers: `sp-05-tasks`, `process-pr-reviews`, and any agent that creates structured beads tasks.

## Task Type Classification

| Type  | Name           | Description                                                               |
| ----- | -------------- | ------------------------------------------------------------------------- |
| **A** | Testable code    | Domain logic, parsers, node types, tools — full ATDD + TDD               |
| **B** | Docs/spec pages  | SYML-SPECIFICATION.md, SYML-SPEC-REVIEW.md — write + review              |
| **D** | Documentation    | README, CLAUDE.md updates — write + lint                                 |
| **E** | Configuration    | pyproject.toml, justfile, pre-commit config, CI — change + validate      |
| **F** | Remediation      | Review-generated fixes — TDD chain if testable, flat task otherwise      |

## Type A: ATDD/TDD Chain

> **RED tasks self-commit, do not push.** The chain stays split into
> Red/Green/Refactor. A Red task commits its known-failing test locally via
> `.venv/bin/python -m tools.commit_red <id>` (with `[skip ci]`, linters
> still run) and does **not** push; the following Green task's push lands that
> commit as a non-tip ancestor, keeping the branch tip green. See the RED/GREEN
> commit guidance in [`references/description-templates.md`](references/description-templates.md).

For each user story with testable code, generate this dependency chain:

```
US<N>: <story title>                                (parent)
  Write acceptance test for US<N>                   (no blockers)
  Red: write failing test for <behavior-1>          (blocked by acceptance test)
  Green: make <behavior-1> pass                     (blocked by Red-1)
  Refactor: clean up <behavior-1>                   (blocked by Green-1)
  Red: write failing test for <behavior-2>          (blocked by Refactor-1)
  Green: make <behavior-2> pass                     (blocked by Red-2)
  Refactor: clean up <behavior-2>                   (blocked by Green-2)
  ...
  Verify acceptance test passes for US<N>           (blocked by last Refactor)
```

> **The Red/Green/Refactor leaf titles ARE the unit-level Test List** (authored at
> `/sp:05-tasks`). Each leaf is one Test List entry — a _title_, not a pre-written
> test. The concrete test is written just-in-time when its `Red:` leaf is worked.
> This is what keeps the project on the Canon-TDD side of "list = titles, not
> pre-written tests" (see `/test-driven-development` → `## Test List`).
>
> **Conservative discovery.** When implementing a leaf reveals a _new_ required
> behavior not already on the list, file a new Red/Green/Refactor sub-chain
> **parented to the US story** — `br create --parent <US-id>`, **not** parented to
> the implement task — so the discovered work lives in the US subtree. Gating: the
> discovered open children keep the `US<N>:` parent un-retired (prep only retires a
> parent once all children close), and the `Verify acceptance test passes` leaf's
> completeness check is the backstop. The worker does **not** auto-rewire the Verify
> dependency (that "active" rewiring option was declined) — the open children alone
> hold the story open.

### Construction

```bash
ACCEPT_ID=$(br create "Write acceptance test for US<N>" --parent $US_ID \
  --description "..." --json | jq -r '.id')
PREV=$ACCEPT_ID

for each behavior:
  RED=$(br create "Red: write failing test for <behavior>" --parent $US_ID \
    --description "..." --json | jq -r '.id')
  br dep add $RED $PREV
  GREEN=$(br create "Green: make <behavior> pass" --parent $US_ID \
    --description "..." --json | jq -r '.id')
  br dep add $GREEN $RED
  REFACTOR=$(br create "Refactor: clean up <behavior>" --parent $US_ID \
    --description "..." --json | jq -r '.id')
  br dep add $REFACTOR $GREEN
  PREV=$REFACTOR

VERIFY=$(br create "Verify acceptance test passes for US<N>" --parent $US_ID \
  --description "..." --json | jq -r '.id')
br dep add $VERIFY $PREV
```

### Naming Convention

```text
User Story Task:  "US<N>: <title>"
ATDD sub-tasks:   "Write acceptance test for US<N>", "Verify acceptance test passes for US<N>"
TDD sub-tasks:    "Red: write failing test for <behavior>", "Green: make <behavior> pass", "Refactor: clean up <behavior>"
```

## Type B: Docs/Spec Pages

Single task under the user story parent:

```bash
br create "<spec/doc page change description>" --parent $US_ID \
  --description "..." --json
```

Validation: content is accurate and internally consistent — no broken cross-references between `SYML-SPECIFICATION.md` and `SYML-SPEC-REVIEW.md`.

## Type D: Documentation

Single task, no chain needed:

```bash
br create "<doc description>" --parent $PARENT_ID \
  --description "..." --json
```

Validation: file exists with correct content, no broken links or formatting issues.

## Type E: Configuration

Single task, no chain needed:

```bash
br create "<config change description>" --parent $PARENT_ID \
  --description "..." --json
```

Validation: relevant dry-run or check command exits 0.

## Type F: Remediation

For review-generated fix tasks (from security, architecture, or quality reviews).

### Testable code (has a `tests/test_<module>.py` sibling)

Create a parent task with Red-Green-Refactor sub-chain. As in Type A, the Red
task self-commits its failing test via
`.venv/bin/python -m tools.commit_red <id>` and does **not** push; the
following Green push lands it with a green tip.

```bash
REMEDIATE_ID=$(br create "Remediate: <finding title>" --parent $PARENT_ID \
  --description "..." --json | jq -r '.id')

RED=$(br create "Red: write failing test for <finding>" --parent $REMEDIATE_ID \
  --description "..." --json | jq -r '.id')
GREEN=$(br create "Green: fix <finding>" --parent $REMEDIATE_ID \
  --description "..." --json | jq -r '.id')
br dep add $GREEN $RED
REFACTOR=$(br create "Refactor: clean up <finding> fix" --parent $REMEDIATE_ID \
  --description "..." --json | jq -r '.id')
br dep add $REFACTOR $GREEN
```

### Non-testable (config, docs, simple fix)

Single flat task — same as Types D/E:

```bash
br create "[<review-type>] <finding title>" --parent $PARENT_ID \
  --description "..." --json
```

## Description Templates

All task description templates (parameterized with `<placeholder>` variables) are in [`references/description-templates.md`](references/description-templates.md).

**CRITICAL**: Task descriptions are the ONLY context ralph passes to claude. They must be fully self-contained — a fresh claude session must be able to implement the task without exploring the codebase from scratch.
