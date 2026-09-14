# Resource Limits & Denial-of-Service Prevention

## Purpose

A parsing library has no network layer to rate-limit, but it has the
equivalent problem: a caller can hand `syml.loads`/`syml.load` an arbitrarily
large or adversarially-shaped document. Without bounds, a single call can
exhaust CPU (catastrophic regex backtracking), memory (huge input held in
full), or the stack (deep recursion), turning one parse into a
denial-of-service for the calling process.

## When to Apply Resource Limits

Apply a limit whenever an untrusted document reaches the parser:

- Config files loaded from a repo a CI job doesn't fully control
- Any SYML document accepted over a network boundary (uploaded, fetched, or
  received from another service)
- Batch processing of many documents from an external source

Trusted, developer-authored fixtures in this repo's own test suite do not
need these limits applied at the call site — they need coverage from the
*attacker's* perspective in the test suite instead (see Testing below).

## Resource Limit Categories

| Resource        | Attack shape                                   | Mitigation                                    |
| --------------- | ----------------------------------------------- | ---------------------------------------------- |
| Input size       | Multi-gigabyte document                         | Caller-enforced size cap before calling `load` |
| Recursion depth  | Thousands of nested list/mapping levels          | Depth counter in `incorporate_node`/tree walk  |
| Regex backtracking | Pathological strings against grammar terminals | Avoid nested-quantifier patterns; fuzz them    |
| Line count       | Millions of blank/comment lines                 | Caller-enforced line cap, or streaming parse   |

## Recursion Depth Limiting

`incorporate_node` climbs the parent chain by indentation level, and
`TextLeafNode` accumulates children for multiline values. Both are
recursive/iterative structures whose cost scales with nesting depth supplied
by the input itself — not by anything the library controls internally.

```python
# Illustrative pattern: bound recursive tree operations by an explicit depth
# limit rather than relying on Python's default recursion limit, which
# raises an unstructured RecursionError deep inside third-party code
# (Parsimonious) rather than a typed ParseError at the library boundary.

MAX_NESTING_DEPTH = 500


def incorporate_node(tip: "SymlNode", node: "SymlNode", depth: int = 0) -> "SymlNode":
    if depth > MAX_NESTING_DEPTH:
        raise ParseError(
            f"exceeded max nesting depth ({MAX_NESTING_DEPTH})",
            filename=node.filename,
        )
    # ... existing climb-the-parent-chain logic ...
    return tip
```

Prefer converting an unbounded recursive walk to an explicit loop with a
depth counter over raising Python's recursion limit — raising the limit only
moves the crash point and makes a stack-exhaustion segfault more likely
instead of a clean `RecursionError`.

## Input Size Limiting (Caller Responsibility + Library Documentation)

`syml.loads`/`syml.load` should document, not silently assume, that they do
not enforce a size limit themselves — that decision belongs to the caller
that knows its trust boundary. What the library *can* do is avoid
multiplying a large input's cost (e.g. avoid `O(n^2)` string operations
during lexing).

```python
# Caller-side pattern for an untrusted-input boundary (e.g. a web service
# that accepts SYML uploads) — not something syml itself needs to impose.
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # 10 MiB


def load_untrusted(raw: bytes, filename: str) -> dict[str, object]:
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"document exceeds {MAX_DOCUMENT_BYTES} bytes")
    return syml.loads(raw.decode("utf-8"), filename=filename)
```

## Regex / Grammar Backtracking (ReDoS)

Parsimonious PEG grammars are still susceptible to backtracking blowup if a
rule's regex terminal has nested quantifiers or ambiguous alternation
against long adversarial strings (e.g. `"   " * 100000` against an
indent-matching rule, or a comment line with no terminator repeated many
times).

```python
# ❌ Vulnerable shape: nested quantifiers over attacker-controlled length
BAD_PATTERN = r"(\s*)+:"

# ✅ Prefer a single bounded quantifier per character class
GOOD_PATTERN = r"\s*:"
```

Stress-test any regex terminal with long, near-matching (but not fully
matching) strings — that is where catastrophic backtracking shows up, not
in strings that match cleanly or fail immediately.

## Testing Resource Limits

### Unit Tests

```python
import pytest

import syml
from syml.basetypes import ParseError


def test_it_should_reject_input_beyond_max_nesting_depth() -> None:
    """A pathologically deep list should raise ParseError, not RecursionError."""
    deeply_nested = "\n".join(
        f"{'  ' * i}- item" for i in range(2000)
    )
    with pytest.raises(ParseError):
        syml.loads(deeply_nested)


def test_it_should_parse_within_bounded_time_for_long_lines() -> None:
    """A very long single line must not trigger catastrophic backtracking."""
    import time

    pathological = "key: " + ("a" * 200_000)
    start = time.monotonic()
    syml.loads(pathological)
    assert time.monotonic() - start < 1.0
```

### Property-Based Tests

```python
from hypothesis import given, settings, strategies as st

import syml


@given(st.integers(min_value=1, max_value=5000))
@settings(deadline=None)
def test_it_should_never_hang_on_arbitrary_nesting_depth(depth: int) -> None:
    """Parsing must terminate (raise or succeed) regardless of nesting depth."""
    doc = "\n".join(f"{'  ' * i}- x" for i in range(depth))
    try:
        syml.loads(doc)
    except Exception:  # noqa: BLE001 -- any typed failure is acceptable here
        pass
```

## Security Best Practices

### 1. Fail Fast, Fail Typed

Every resource-limit violation should raise a typed `ParseError` (or a
documented subclass), never let Python's own limits (`RecursionError`,
`MemoryError`) escape uncaught from inside the grammar.

### 2. Separate Library Limits From Caller Policy

The library enforces limits that protect its own internals (recursion
depth, backtracking-safe regexes). Size and rate limits that depend on the
caller's trust model (how big is "too big" for *this* deployment) belong at
the call site, documented so callers know they must add them.

### 3. Log Enough to Diagnose, Not Enough to Leak

If a resource-limit rejection is logged, include the limit and the
input's size/depth, not the full untrusted content.

### 4. Test From the Attacker's Perspective

Fuzz and property-test entry points (`loads`, `load`) with adversarial
shapes (deep nesting, pathological regex inputs, huge single lines) as a
standing part of the test suite, not a one-off manual check.

## Common Mistakes

### ❌ Relying on Python's Default Recursion Limit

```python
# Crashes with an unstructured RecursionError deep in Parsimonious/visitor
# code instead of raising a typed ParseError at the library boundary.
def climb(node):
    return climb(node.parent) if node.parent else node
```

### ❌ Assuming Small Test Fixtures Represent Worst-Case Input

Correctness tests use small, readable fixtures. Resource-limit tests need
their own adversarially-shaped fixtures (deep nesting, long lines,
near-matching regex input) — the two suites test different properties.

### ✅ Explicit Depth Counter With a Typed Error

```python
def incorporate_node(tip, node, depth=0):
    if depth > MAX_NESTING_DEPTH:
        raise ParseError("exceeded max nesting depth", filename=node.filename)
    return incorporate_node(tip.parent, node, depth + 1) if not tip.can_add_node(node) else tip
```

## Related Skills

- **security-audit**: Untrusted-input handling, ReDoS, file handling
- **quality-review**: Test quality for adversarial/property-based cases
