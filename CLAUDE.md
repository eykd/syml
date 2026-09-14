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

Parsing is line-oriented and context-free at the grammar level. `src/syml/parsers.py` holds a Parsimonious PEG grammar in which every line lexes independently as `indent (comment / blank / structure / value)`. The `SymlParser(NodeVisitor)` turns each line into a `SymlNode` from `src/syml/nodes.py`, tagged with its indentation level.

Tree building happens after lexing, in `visit_lines`: it walks the flat list of line nodes and calls `incorporate_node` on the current tip. `incorporate_node` climbs the parent chain by indentation level until it finds a node whose `can_add_node` accepts the newcomer. `ContainerNode` (the base of `Root`, `KeyValue`, `ListItem`) auto-inserts a `Mapping` or `List` intermediary when it receives a bare `KeyValue` or `ListItem`. `TextLeafNode` accepts further `TextLeafNode`s as children, which is how multiline values accumulate. When no ancestor accepts a node, `OutOfContextNodeError` is raised (subclass of `ParseError`, itself a `ValueError`); it is listed in `unwrapped_exceptions` so Parsimonious does not wrap it.

Two renderings exist on every node: `as_data()` returns plain `str`/`list`/`dict`, and `as_source()` returns `Source` objects from `src/syml/basetypes.py`. `Source` carries filename plus start/end `Pos` (index, line, column) and compares and hashes by its text, so it works interchangeably with strings as dict keys.

## Spec vs. implementation

`SYML-SPECIFICATION.md` (v1.1) was written ahead of the parser and deliberately breaks compatibility with the shipped 0.6.2 behavior. `todo.txt` is the empirically verified list of conformance gaps between the two, and `SYML-SPEC-REVIEW.md` records the design decisions (D1–D17) behind v1.1. Do not assume the parser matches the spec; check `todo.txt` before "fixing" behavior in either direction, and settle open spec questions noted there before implementing.

## Conventions

- mypy is strict and covers `tests/` too: every test function needs `-> None` and fixtures need return annotations.
- ruff runs in preview mode with single quotes inline and double quotes for docstrings; public functions and classes need docstrings (pydocstyle `D` rules).
- Unreachable branches satisfy the coverage gate with `# pragma: nocover` / `# pragma: nobranch`, which is the established pattern in `nodes.py` and `parsers.py`.
- Tests run in random order, so they must not depend on each other. New pytest markers must be registered in pyproject (`--strict-markers`).
