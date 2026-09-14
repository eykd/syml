# Solution Index

Solutions are organized by category. Each entry links to a detailed solution document.

## Categories

| Category              | Description                                              |
| ---------------------- | --------------------------------------------------------- |
| `python-typing/`       | mypy strict mode, generics, protocol/type-guard patterns  |
| `ruff/`                | Preview-mode lint rules, pydocstyle, formatting conflicts |
| `pytest-coverage/`     | 100% branch coverage patterns, pragma usage, fixtures     |
| `parsing/`             | Parsimonious grammar quirks, PEG lexing/tree-building     |
| `spec-conformance/`    | Spec-vs-implementation gaps, todo.txt/D1-D17 traceability |
| `security/`            | Input validation, resource limits, unsafe-input handling  |
| `clean-architecture/`  | Layer boundaries, node hierarchy, dependency direction    |
| `tooling/`             | `just` recipes, pre-commit hooks, `uv`/`br` dependency issues |

## Solutions

_(none yet — entries are added here as they are discovered, one file per
category directory, e.g. `tooling/<slug>.md`, linked from this index.)_

## How to Update This File

When a session resolves a non-obvious gotcha, add an entry under the matching
category using this format:

    ### category

    - [Short Problem Title](category/slug.md) — one-line summary of the fix (YYYY-MM-DD)
