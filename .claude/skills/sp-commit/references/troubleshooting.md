# Commit Troubleshooting

## Pre-commit Hook Failures

### Linting Errors

```bash
# Fix automatically
just fix

# Or manually fix and retry commit
```

### Type Errors

```bash
# Check types
uv run mypy

# Fix errors and retry commit
```

### Test Failures

```bash
# Run tests
uv run pytest

# Fix failing tests and retry commit
```

### Coverage Gate Failures

```bash
# The pre-commit pytest-check hook runs with --cov-fail-under=100.
# Find the uncovered lines and add tests, or mark genuinely
# unreachable branches with # pragma: nocover / # pragma: nobranch
# (see nodes.py and parsers.py for the established pattern).
uv run pytest --cov-report=term-missing
```

### `uv-lock` Failures

```bash
# uv.lock is out of sync with pyproject.toml
uv lock
git add uv.lock
```

## Commit Message Validation Failures

### Common Line-Length Errors

**Error: a body or subject line exceeds 100 characters**

One or more body lines exceed 100 characters.

Fix: Manually wrap long lines at natural break points:

```bash
# Before (fails)
git commit -m "feat: add feature

This is a very long line that exceeds one hundred characters and will cause the commit to fail."

# After (passes)
git commit -m "feat: add feature

This is a very long line that exceeds one hundred characters and
will cause the commit to fail."
```

**Other validation rules:**

- Ensure commit message follows conventional commit format
- Check that type is valid (feat, fix, docs, etc.)
- Subject line should be lowercase
- No period at end of subject line
- Subject line max 100 characters

## Python Project Commit Scenarios

### New Feature with Tests

```
feat: add [feature name]

- Implement [component/function]
- Add comprehensive test coverage
- Update types/interfaces as needed
```

### Bug Fix

```
fix: resolve [issue description]

- Fix [specific problem]
- Add regression test
```

### Configuration Changes

```
chore: update [tool] configuration

- Adjust [setting] for [reason]
- Impact: [description]
```

### Dependency Updates

```
chore: update dependencies

- Update [package] to v[version]
- Reason: [security/feature/bugfix]
```
