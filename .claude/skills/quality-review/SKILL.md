---
name: quality-review
description: Review code for quality, correctness, and test quality. Use when reviewing PR changes for code quality without security or architecture concerns (those have dedicated skills).
---

# Quality Review Skill

Review pull requests for code quality, correctness, and test quality while excluding security and architecture concerns (handled by dedicated skills).

## Style Requirements

**CRITICAL**: Write for non-technical managers using plain English (6th-grade reading level).

- **Report problems only** - never acknowledge what's done well or include praise
- **Target 30-second scan time** - compress findings to 2-3 lines maximum
- **Use plain language** - no unnecessary jargon
- **Focus on fixes** - one-sentence problem, one-line fix
- **Conditional sections** - only show sections with problems

## Review Process

1. **Get PR diff**: Use `gh pr diff <number>` to get branch changes
2. **Check known issues**: Read `known-issues.json` if present to avoid re-reporting tracked beads tasks
3. **Analyze changes**: Evaluate correctness, test quality, simplicity, code quality
4. **Organize findings**: Group by severity (Critical → High → Medium → Low)
5. **Post review**: Use concise compressed format

### 2. Does It Work

Evaluate correctness and production-readiness:

- **Correctness**: Does the code do what it's supposed to do?
- **Edge cases**: Are error conditions and boundary cases handled?
- **Testing**: Are there tests that demonstrate it works?
- **Production-ready**: Will this work in production environments?

**Critical checks**:

- All paths tested
- Error handling present
- No obvious bugs
- Follows expected behavior

### 3. Test Quality

See [references/test-desiderata.md](references/test-desiderata.md) for detailed guidance.

Evaluate using Kent Beck's Test Desiderata:

- **Isolated**: Can tests run independently?
- **Composable**: Can tests run in any combination?
- **Fast**: Quick feedback?
- **Deterministic**: Same result every run?
- **Readable**: Clear what's being tested?
- **Behavioral**: Tests outcomes, not implementation?
- **Specific**: Clear failure messages?
- **Predictive**: Catches real bugs?

Check for anti-patterns:

- Missing assertions
- Shared mutable state
- Excessive mocking
- Logic in tests

**Coverage verification**:

- Run `uv run pytest` (coverage runs by default; the pre-commit hook and CI
  enforce `--cov-fail-under=100`)
- Project requires 100% coverage across `src/` and `tools/`
- Flag any coverage below 100% as HIGH severity

### 4. Simplicity

Evaluate maintainability and code clarity:

- **Simple vs complex**: Is this the simplest solution that works?
- **Readable**: Can another developer understand this quickly?
- **Maintainable**: Will this be easy to modify later?
- **Appropriate abstractions**: Right level of abstraction for the problem?

**Watch for**:

- Over-engineering (unnecessary abstractions, premature optimization)
- Under-engineering (copy-paste code, missing obvious patterns)
- Clever code (hard to understand, shows off rather than solves)

### 5. Code Quality

Check compliance with CLAUDE.md project standards:

- **mypy strictness**: `disallow_untyped_defs`, `disallow_any_generics`,
  `check_untyped_defs`, `warn_unused_ignores` all honored; every test
  function has a `-> None` return annotation and fixtures are annotated
- **ruff compliance**: No warnings from `ruff check` (preview mode); no
  bare `Any` without justification (`ANN401`)
- **Naming conventions**: Domain vocabulary matches `CLAUDE.md`'s
  architecture terms (`SymlNode`, `ContainerNode`, etc.), proper naming
- **Docstrings**: All public functions/classes documented (pydocstyle `D`
  rules enforced by ruff)
- **Import order**: Correct and alphabetized (ruff `I` rules)
- **Formatting**: `ruff format` compliance (single quotes inline, double
  quotes for docstrings)

**Project-specific rules**:

- 100% test coverage threshold (`--cov-fail-under=100`)
- Conventional commit format
- Zero warnings policy
- Coverage gate is enforced by the pre-commit hook and CI, not by
  `pyproject.toml` alone — a green local `uv run pytest` can still fail
  on commit

### 6. Error Handling Standards

Check compliance with this repo's parser error conventions:

- **Typed exceptions only**: Parsing failures raise `ParseError` (or the
  `OutOfContextNodeError` subclass), never an unhandled `RecursionError`,
  `KeyError`, or bare `Exception` escaping from inside the grammar
- **Error hierarchy**: `OutOfContextNodeError` is a subclass of `ParseError`,
  itself a `ValueError`; keep new error types within this hierarchy
- **Position info**: Errors carry `Pos`/`Source` context useful to the
  caller, not internal parser/visitor state
- **No error disclosure**: Error messages don't leak more of the host
  filesystem or environment than the caller already provided via `filename`

**Checklist items**:

- [ ] New failure modes raise `ParseError` or a documented subclass
- [ ] `unwrapped_exceptions` is updated if a new exception type must bypass
      Parsimonious's wrapping
- [ ] Error messages include position/filename context where available
- [ ] No stack traces or internal parser state in user-facing messages

### 7. Validation Architecture

Check compliance with validation-architecture reference in ddd-domain-modeling skill:

- **Three-layer validation**: Presentation (format), Domain (business rules), Infrastructure (constraints)
- **No duplication**: Each validation check in exactly one layer
- **Presentation layer**: Format validation (StringValidator, AllowlistValidator) returns 422
- **Domain layer**: Business rules in entity constructors, throws ValidationError
- **Infrastructure layer**: Uniqueness constraints caught, throw ConflictError

**Checklist items**:

- [ ] Format validation at presentation boundary
- [ ] Business rules in domain entities/value objects
- [ ] No duplicate validation across layers
- [ ] UNIQUE constraint violations caught and mapped to ConflictError
- [ ] Validation errors have clear messages

### 8. Domain Modeling

Check compliance with ddd-domain-modeling skill:

- **No primitive obsession**: Use value objects for IDs, emails, money (not raw strings/numbers)
- **Domain entities pure**: No database methods (toRow, fromRow) in entities
- **Repository interfaces in domain**: Interface in domain/interfaces/, implementation in infrastructure
- **Value object immutability**: Value objects have no setters, create new instance for changes

**Checklist items**:

- [ ] IDs use value objects (UserId, TaskId), not string
- [ ] Emails use Email value object, not string
- [ ] No toRow() methods in domain entities
- [ ] Repository interfaces in domain/interfaces/
- [ ] Value objects are immutable

### 9. Datetime Handling

Check compliance with portable-datetime skill:

- **UTC storage**: All timestamps stored as ISO 8601 UTC strings (string type, not Date)
- **UTC calculations**: Use setUTC* and getUTC* methods, never local time methods
- **Timezone conversion at boundary**: Convert to user timezone only at presentation layer
- **Time injection for tests**: Tests use injected time function, not new Date()

**Checklist items**:

- [ ] Timestamps stored as UTC ISO strings (string type)
- [ ] No Date objects in domain entities (use string)
- [ ] Calculations use UTC methods only
- [ ] No local time methods (setDate, getDate, setHours)
- [ ] Tests inject time, don't use new Date() directly

## Known Issues Handling

See [references/known-issues.md](references/known-issues.md) for details.

Before reporting findings:

1. Check if `known-issues.json` exists in workspace
2. Parse JSON for tasks with status "open" or "ready"
3. If finding relates to a known issue, reference it: "Related to beads task syml-123"
4. Only report NEW findings not already tracked

## Priority Levels

See [references/priority-levels.md](references/priority-levels.md) for definitions.

### Must Fix (Blocks Merge)

- Correctness issues or bugs
- Failing tests or missing test coverage
- Project standard violations (CLAUDE.md)
- Breaking changes without justification

### Should Fix (Important but Not Blocking)

- Test quality improvements
- Simplicity enhancements
- Missing edge case handling
- Maintainability concerns

### Consider (Optional Suggestions)

- Style preferences beyond standards
- Future enhancement ideas
- Alternative approaches
- Minor optimizations

## Output Format

**COMPRESSED FORMAT** (2-3 lines per finding):

```markdown
## Code Quality Review

### Critical

- src/syml/parsers.py:45: Missing error handling - unhandled exception escapes
  Fix: Wrap in a typed ParseError instead of letting it propagate raw

### High

- tests/test_parsers.py:0: Test coverage below 100% - missing edge case tests
  Fix: Add tests for empty input and malformed-line handling

- src/syml/nodes.py:12: Using untyped `Any` - violates mypy strictness
  Fix: Define a proper type/protocol for the node data

### Medium

- src/syml/parsers.py:67: Function too complex - 8 levels of nesting
  Fix: Extract validation logic to separate function

## Copy-Paste Prompt for Claude Code

**REQUIRED when findings exist** (3-5 lines maximum):
```

Add error handling to src/syml/parsers.py:45 raising a typed ParseError.
Add edge case tests to tests/test_parsers.py for empty input and malformed lines.
Replace untyped `Any` in src/syml/nodes.py:12 with a proper type.
Extract validation logic from src/syml/parsers.py:67 to reduce nesting.

```

**DO NOT include:**
- ~~"What Changed", "Does It Work", "Test Quality", "Simplicity"~~ sections - use compressed findings only
- ~~"None found"~~ sections - omit sections with no issues
- ~~Praise or positive feedback~~ - focus exclusively on problems
- ~~Lengthy explanations~~ - keep to 2-3 lines per finding

```

## Integration Notes

### Relationship to Other Review Skills

- **security-audit**: Handles untrusted-input, ReDoS, recursion, secrets
- **clean-architecture-validator**: Handles dependency violations, layer boundaries
- **quality-review** (this skill): Handles correctness, test quality, simplicity, code standards

**DO NOT overlap** - if a finding is about security or architecture, don't report it here.

### Related Skills

This skill works together with:

- **ddd-domain-modeling**: Value objects, entities, validation architecture, domain purity
- **pytest-unit-testing**: Test patterns, fixtures, achieving 100% coverage
- **security-audit**: Error disclosure prevention, safe error responses
- **clean-architecture-validator**: Layer boundaries, dependency rules

When reviewing code, check these skills for detailed guidance on specific patterns.

### GitHub Actions Context

This skill is designed for GitHub Actions workflows with:

- `gh` CLI available for PR operations
- `known-issues.json` generated from beads tasks
- CLAUDE.md project standards in repository
- pytest with coverage reporting (`--cov-fail-under=100`)

### Local Usage

Can also be used locally for PR review:

```bash
# Review a specific PR
/quality-review

# Skill will prompt for PR number if not in GitHub Actions context
```

## Edge Cases

- **No changes**: Report "No changes detected" and exit gracefully
- **No known-issues.json**: Skip known issues check, report all findings
- **Very large PRs**: Focus on highest-impact changes, note review limitations
- **No tests changed**: Skip test quality section, focus on other areas
