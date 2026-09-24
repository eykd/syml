# Priority Levels Reference

Guidance for categorizing findings by priority in quality reviews.

---

## Overview

Findings are organized into three priority levels to help reviewers and developers focus on what matters most. Each level has clear criteria for what belongs and what action is expected.

---

## Must Fix (Blocks Merge)

**Definition**: Issues that make the code incorrect, untestable, or violate non-negotiable project standards.

**Action Required**: These MUST be resolved before the PR can be merged.

### Categories

#### Correctness Issues

- Logic errors or bugs
- Incorrect behavior vs specification
- Breaking changes without justification
- Missing error handling for critical paths
- Data corruption risks

**Example**:

```markdown
**Incorrect calculation in discount logic** - src/syml/parsers.py:42

- **Problem**: Discount percentage applied twice (line 42 and line 45)
- **Impact**: Customers charged incorrect amounts
- **Fix**: Remove duplicate discount application on line 45
```

#### Failing or Missing Tests

- Tests fail when run
- Zero test coverage for new code
- Missing tests for critical functionality
- Coverage below 100% threshold

**Example**:

```markdown
**No tests for payment processing** - tests/test_parsers.py

- **Problem**: New payment logic has no test coverage
- **Impact**: Pre-commit hooks will fail; payment bugs could reach production
- **Fix**: Add unit tests covering success, failure, and timeout scenarios
```

#### Project Standard Violations

- Violations of CLAUDE.md requirements
- mypy strict-mode violations (missing annotations, untyped defs)
- ruff errors (not warnings)
- Missing required docstrings on public functions/classes (pydocstyle `D`)
- Incorrect naming conventions

**Example**:

```markdown
**Function missing type annotation** - src/syml/basetypes.py:12

- **Problem**: `as_data()` has no return type annotation
- **Impact**: Violates mypy strict mode (`disallow_untyped_defs`)
- **Fix**: Add `-> dict[str, object]` return type annotation
```

---

## Should Fix (Important but Not Blocking)

**Definition**: Issues that reduce code quality, maintainability, or test effectiveness but don't make the code incorrect.

**Action Required**: Should be addressed before or shortly after merge. Can merge with these if acknowledged.

### Categories

#### Test Quality Improvements

- Test anti-patterns (excessive mocking, logic in tests)
- Tests that are hard to understand
- Missing edge case coverage (when code handles them)
- Violation of Test Desiderata properties

**Example**:

```markdown
**Excessive mocking in order tests** - tests/test_nodes.py:30

- **Problem**: Test mocks 5 dependencies when 2 would suffice
- **Impact**: Tests are brittle and hard to maintain
- **Fix**: Use real value objects for Order and LineItem, mock only NotificationService and PaymentGateway
```

#### Simplicity Concerns

- Over-engineering (premature abstractions)
- Code duplication that should be extracted
- Complex logic that could be simplified
- Missing helper functions for repeated patterns

**Example**:

```markdown
**Duplicated validation logic** - src/syml/parsers.py and src/syml/nodes.py

- **Problem**: Email validation regex duplicated in 2 places
- **Impact**: Updates require changing multiple locations
- **Fix**: Extract to shared validateEmail() utility function
```

#### Maintainability Issues

- Poor naming (unclear or misleading)
- Functions doing too many things
- Missing comments for complex logic
- Inconsistent patterns with rest of codebase

**Example**:

```markdown
**Unclear variable name** - src/syml/nodes.py:67

- **Problem**: Variable `x` used for order total amount
- **Impact**: Reduces code readability
- **Fix**: Rename to `orderTotal` or `totalAmount`
```

---

## Consider (Optional Suggestions)

**Definition**: Suggestions for improvement that are subjective, non-critical, or represent alternative approaches.

**Action Required**: Optional. Developer can accept, reject, or defer to future work.

### Categories

#### Style Preferences

- Alternative naming suggestions
- Different code organization
- Formatting preferences beyond Prettier
- Comment style variations

**Example**:

```markdown
**Consider renaming for clarity** - src/syml/basetypes.py:15

- **Problem**: `calc()` is generic
- **Impact**: Slightly reduces readability
- **Fix**: Consider `calculateDiscountedPrice()` for more clarity
```

#### Future Enhancements

- Performance optimizations for non-critical paths
- Additional features that could be added
- Refactoring opportunities for future work
- More comprehensive error messages

**Example**:

```markdown
**Future enhancement: batch processing** - src/syml/parsers.py:20

- **Problem**: Emails sent one at a time
- **Impact**: Could be faster with batching
- **Fix**: Consider batching email sends in future if volume increases
```

#### Alternative Approaches

- Different patterns or architectures
- Trade-offs between implementations
- Alternative libraries or techniques
- Design pattern suggestions

**Example**:

```markdown
**Alternative: use Strategy pattern** - src/syml/nodes.py

- **Problem**: Switch statement for pricing types
- **Impact**: Could be more extensible
- **Fix**: Consider Strategy pattern if more pricing types are added
```

#### Minor Optimizations

- Small performance improvements
- Reduced memory allocations
- Slightly better algorithms
- Caching opportunities

**Example**:

```markdown
**Minor optimization opportunity** - src/syml/parsers.py:45

- **Problem**: Array filtered twice sequentially
- **Impact**: Minor performance cost
- **Fix**: Could combine into single filter pass, but current approach is clearer
```

---

## Decision Guidelines

Use these questions to determine priority level:

### Is it "Must Fix"?

- Would this cause incorrect behavior? → **Must Fix**
- Would this fail CI/CD checks? → **Must Fix**
- Does it violate a documented project standard? → **Must Fix**
- Is there missing test coverage? → **Must Fix**

### Is it "Should Fix"?

- Would this make the code harder to maintain? → **Should Fix**
- Does it violate a best practice (not a requirement)? → **Should Fix**
- Is there a clear quality improvement? → **Should Fix**
- Would this cause confusion for other developers? → **Should Fix**

### Is it "Consider"?

- Is this a suggestion, not a problem? → **Consider**
- Are there trade-offs to the proposed change? → **Consider**
- Is this about future enhancements? → **Consider**
- Is this a matter of preference? → **Consider**

---

## When in Doubt

**Err on the side of lower priority**. It's better to suggest something as "Consider" than to block a merge on a subjective issue.

**Consult project standards**. If CLAUDE.md or other project documentation specifies a requirement, it's "Must Fix". If it's a best practice without enforcement, it's "Should Fix".

**Think about impact**. If the issue would cause production problems, data loss, or security issues, it's "Must Fix". If it's about code quality, it's likely "Should Fix" or "Consider".
