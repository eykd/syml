---
name: sp-commit
description: 'Use when: (1) committing session changes, (2) creating conventional commits, (3) handling pre-commit hook failures. Python projects with pre-commit and a 100% coverage gate.'
allowed-tools: [Bash, Read]
---

# Commit Changes

Create git commits following conventional commit format.

## Process

### 1. Review Changes

```bash
git status
git diff
```

### 2. Stage and Commit

**Always stage `.beads/issues.jsonl` alongside your code.** It's the
persisted log of beads state (task closures, new tasks, dep edits).
Losing this delta orphans the state change from the commit that caused
it. Run `git add .beads/issues.jsonl` after staging your task files,
skipping only if `git status` shows it clean.

**Never stage `.sp-harden-state.json` or `.sp-harden-findings.json`.**
They are gitignored workflow state for the `/sp:08-harden` loop, not
project artifacts.

```bash
# Stage specific files (never use -A or .)
git add file1.py file2.py dir/

# Stage beads state if dirty (it's tracked, not gitignored)
git add .beads/issues.jsonl

# Commit with proper format
git commit -m "feat: add new feature

- Implement core functionality
- Add comprehensive test coverage"

git log --oneline -n 3
```

## Commit Message Format

```
<type>: <subject>

<body>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

## Line Length Rules (CRITICAL)

Keep commit messages to a **100-character maximum** for ALL lines:

- **Subject line**: Max 100 characters (including type and colon)
- **Body lines**: Max 100 characters **per line**

**Common mistake**: Writing long sentences that exceed 100 characters.

**Solution**: Wrap lines manually at natural break points.

### Examples

❌ **Bad** (line too long):

```bash
git commit -m "docs: amend constitution to v1.2.1 (strengthen 100% coverage enforcement)

Add comprehensive guidance for achieving 100% test coverage across multiple documentation layers."
# Line exceeds 100 characters
```

✅ **Good** (lines wrapped):

```bash
git commit -m "docs: amend constitution to v1.2.1 (strengthen coverage)

Add comprehensive guidance for achieving 100% test coverage across
multiple documentation layers."
```

### Formatting Lists

When including lists or multiple points, keep each line under 100 chars:

```bash
git commit -m "$(cat <<'EOF'
feat: add multiline value support

Implement multiline text value parsing with the following features:
- Indentation-aware continuation lines
- Trailing-newline normalization
- Source position tracking for error messages

All features include comprehensive test coverage.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Tips for Staying Under 100 Characters

1. **Break at conjunctions**: "and", "but", "or", "with"
2. **Break after punctuation**: Periods, commas, colons
3. **Use HEREDOC** for complex messages (see example above)
4. **Check line length** if a body line exceeds 100 characters

## Important Rules

**Stage files explicitly:**

- ❌ Never use `git add -A` or `git add .`
- ✅ Always specify files: `git add file1.py src/syml/`

**Message quality:**

- Use imperative mood ("add feature" not "added feature")
- Subject line: max 100 characters
- Body: explain WHY, not just WHAT

**Never bypass verification:**

- ❌ Never use `git commit --no-verify` or otherwise skip pre-commit hooks
- ✅ If a hook fails, fix the underlying issue and retry the commit

## Pre-commit Hooks

This project has automatic validation:

- `trailing-whitespace` and `end-of-file-fixer`
- `ruff` (lint) and `ruff-format`
- `uv-lock` (keeps `uv.lock` in sync with `pyproject.toml`)
- `mypy-check` (type checking)
- `pytest-check` (full test suite with the 100% coverage gate,
  `--cov-fail-under=100`)

Hooks run automatically. If commit fails, fix issues and retry.

## Reference

- **[troubleshooting.md](references/troubleshooting.md)** — Hook failures, message validation, commit scenarios
