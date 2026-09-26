# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`syml` is a small Python library (published on PyPI) that parses SYML, a YAML-like markup language where every leaf value is a plain string. Public API is `syml.loads(text, filename=None)` and `syml.load(file_obj, filename=None)`. Python ≥3.12, packaged with hatchling, managed with `uv`.

Prerequisites beyond `uv`: `br` (beads_rust) ≥ 0.5.5 (`just beads-init` installs the pinned release), `jq`, `just`, and `bash` (the ralph skill's `prep.sh` uses process substitution).

## Commands

```sh
uv sync --all-groups                 # install runtime + dev + test groups
uv run pytest                        # full suite (addopts already add --cov, --random-order, -vv, --strict-markers/config)
uv run pytest tests/test_parsers.py::TestSymlParser::test_it_should_parse_a_simple_text_value --no-cov
uv run ruff check --fix && uv run ruff format
uv run mypy                          # file set is configured in pyproject; no args needed
./runtests.sh                        # fast loop: ruff fix+format, pytest --exitfirst --failed-first --new-first, then mypy (rewrites files)
./watchtests.sh                      # re-runs runtests.sh on every .py change (needs `entr`)
just check                           # lint + type-check + test (the recipe names the /sp:* workflow calls)
just fix                             # ruff format + ruff check --fix
just acceptance                      # pytest-bdd acceptance suite (tests/acceptance, never part of `uv run pytest`)
just acceptance-missing              # print stub step definitions for every unbound Gherkin step
just beads-init                      # install pinned `br` and rebuild .beads/beads.db from issues.jsonl
```

The 100% coverage gate (`--cov-fail-under=100`) is enforced only by the pre-commit hook and CI (`.github/workflows/ci.yaml`), not by pyproject. A green local `uv run pytest` can still fail on commit. Pre-commit also runs ruff, mypy, and `uv-lock`.

pyproject is the single source of tool config: the old `.coveragerc`, `tox.ini`, and `.travis.yml` were removed (a `.coveragerc` silently overrides `[tool.coverage.*]` in pyproject, so never reintroduce one). Coverage covers `src/` and `tools/`; mypy covers `src/`, `tests/`, and `tools/`.

Acceptance tests are pytest-bdd: Gherkin lives in `specs/acceptance-specs/US<NN>-<slug>.feature`, bindings in `tests/acceptance/test_us<nn>_<slug>.py` marked `acceptance`. The unit run both deselects that marker and `--ignore`s `tests/acceptance`, so only `just acceptance` runs them.

## Architecture

Parsing is line-oriented and context-free at the grammar level. `src/syml/parsers.py` holds a Parsimonious PEG grammar in which every line lexes independently as `comment / (indent (structure / data))` under `document = (line "\n")* line?`. The `SymlParser(NodeVisitor)` turns each line into a `SymlNode` from `src/syml/nodes.py`, tagged with its indentation level; `visit_line` drops a column-0 comment line (and any blank line) by returning `None`, so no node is ever built for it.

Tree building happens after lexing, in `visit_document`: it flattens the parsed lines and calls `incorporate_node` on the current tip for each one. `incorporate_node` climbs the parent chain by indentation level until it finds a node whose `can_add_node` accepts the newcomer. `ContainerNode` (the base of `Root`, `KeyValue`, `ListItem`) auto-inserts a `Mapping` or `List` intermediary when it receives a bare `KeyValue` or `ListItem`. `TextLeafNode` accepts further `TextLeafNode`s as children, which is how multiline values accumulate. When no ancestor accepts a node, `OutOfContextNodeError` is raised (subclass of `ParseError`, itself a `ValueError`); it is listed in `unwrapped_exceptions` so Parsimonious does not wrap it.

Two renderings exist on every node: `as_data()` returns plain `str`/`list`/`dict`, and `as_source()` returns `Source` objects from `src/syml/basetypes.py`. `Source` carries filename plus start/end `Pos` (index, line, column) and compares and hashes by its text, so it works interchangeably with strings as dict keys.

## Spec vs. implementation

`syml` 1.0.0 is the conforming reference implementation of `SYML-SPECIFICATION.md` (Version 1.0). `SYML-SPEC-REVIEW.md` records the design decisions (D1–D25) and B-/M-numbered findings behind that conformance work. Cite one of those decisions/findings or an FR-NNN requirement from the current feature's plan before changing behavior in either direction; an open spec question may be settled by a spec edit landing in the same commit as the behavior change that exposed it.

## Conventions

- mypy is strict and covers `tests/` too: every test function needs `-> None` and fixtures need return annotations.
- ruff runs in preview mode with single quotes inline and double quotes for docstrings; public functions and classes need docstrings (pydocstyle `D` rules).
- `src/` carries only `if TYPE_CHECKING:` pragmas, enforced by a test in `tests/test_nodes.py`; an unreachable stub is deleted or tested directly instead of pragma'd.
- Tests run in random order, so they must not depend on each other. New pytest markers must be registered in pyproject (`--strict-markers`).

## Spec-kit workflow

The `/sp:*` commands drive a spec-first workflow; see `.claude/commands/sp/README.md` for the full architecture. Phase order: `/sp:01-brainstorm` → `/sp:02-specify` → `/sp:03-plan` → `/sp:04-red-team` → `/sp:05-tasks` → `/sp:06-analyze` → `/sp:07-implement` → `/sp:08-harden`. `/sp:next` and `/sp:shepherd` drive the loop across phases; `/ralph` drains the beads leaf-task queue within a phase. The constitution lives at `.specify/memory/constitution.md`.

## Specs

Read `specs/readme.md` (the Pin) first — it indexes every feature spec by keyword. Feature directories live at `specs/NNN-<slug>/`; acceptance features live in `specs/acceptance-specs/`.

## Beads Task Management

Always pass `--description` when creating a task. Always parent new tasks to the branch epic found via `scripts/find-branch-epic.sh`. Run `br sync --flush-only` before committing, and stage `.beads/issues.jsonl` together with the code it tracks.

## Orchestration

Orchestration runs in the main session, never in a subagent, because subagents cannot spawn subagents — an orchestrator delegated to a subagent would have no way to dispatch the leaf work it plans.

## Landing the Plane

**When ending a work session**, complete all steps below. Work is NOT complete until `git push` succeeds.

1. File issues for remaining work.
2. Run quality gates (if code changed) — tests, linters, mypy.
3. Update issue status — close finished work, update in-progress items.
4. **Push to remote** (mandatory):
   ```bash
   git pull --rebase
   br sync --flush-only
   git push
   git status  # MUST show "up to date with origin"
   ```
5. Clean up — clear stashes, prune remote branches.
6. Verify all changes are committed AND pushed.
7. Hand off — provide context for the next session.

Never stop before pushing, and never say "ready to push when you are" — push it yourself.

<!-- BEGIN BEADS INTEGRATION -->

## Issue Tracking with br (beads)

**IMPORTANT**: This project uses **br (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why br?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
br ready --json
```

**Create new issues:**

```bash
br create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
br create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:br-123 --json
```

**Claim and update:**

```bash
br update <id> --claim --json
br update br-42 --priority 1 --json
```

**Complete work:**

```bash
br close br-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `br ready` shows unblocked issues
2. **Claim your task atomically**: `br update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `br create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `br close <id> --reason "Done"`

### Auto-Sync

br automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- Use br for ALL task tracking
- Always use `--json` flag for programmatic use
- Link discovered work with `discovered-from` dependencies
- Check `br ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->
