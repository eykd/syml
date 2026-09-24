# Test Quality Evaluation Reference

Guidance for evaluating test quality in pull request reviews.

---

## When to Apply

Evaluate test quality when the PR includes test files:

- `test_*.py` under `tests/` (this repo's pytest convention:
  `tests/test_parsers.py::TestSymlParser::test_it_should_...`)
- `tests/acceptance/test_us<nn>_<slug>.py` (pytest-bdd bindings, marked
  `acceptance`, only run via `just acceptance`)

---

## Kent Beck's Test Desiderata

Evaluate tests against these 12 properties:

### Core Properties

| Property          | Question                          | Signs of Violation                             |
| ----------------- | --------------------------------- | ---------------------------------------------- |
| **Isolated**      | Can tests run independently?      | Shared state, test order dependencies          |
| **Composable**    | Can tests run in any combination? | Global setup/teardown affecting others         |
| **Deterministic** | Same result every run?            | Time-based, random data, external dependencies |
| **Fast**          | Quick feedback?                   | I/O operations, network calls, large datasets  |

### Structural Properties

| Property                  | Question                            | Signs of Violation                            |
| ------------------------- | ----------------------------------- | --------------------------------------------- |
| **Writable**              | Easy to add new tests?              | Copy-paste boilerplate, complex setup         |
| **Readable**              | Clear what's being tested?          | Magic numbers, unclear assertions, long tests |
| **Behavioral**            | Tests outcomes, not implementation? | Testing private methods, mocking internals    |
| **Structure-insensitive** | Survive refactoring?                | Tightly coupled to implementation details     |

### Meta Properties

| Property       | Question               | Signs of Violation                           |
| -------------- | ---------------------- | -------------------------------------------- |
| **Automated**  | No manual steps?       | Manual assertions, visual inspection needed  |
| **Specific**   | Clear failure message? | Generic assertions, unclear failure location |
| **Predictive** | Catches real bugs?     | Tests only happy path, missing edge cases    |
| **Inspiring**  | Confidence to deploy?  | Low coverage, missing critical paths         |

---

## GOOS Principles

From "Growing Object-Oriented Software, Guided by Tests":

### Test Classification

| Type            | Purpose                   | Characteristics        |
| --------------- | ------------------------- | ---------------------- |
| **Unit**        | Single component behavior | Fast, isolated, no I/O |
| **Integration** | Component collaboration   | Tests real boundaries  |
| **Acceptance**  | User-visible behavior     | End-to-end, slower     |

### Mocking Guidelines

**Mock Roles, Not Objects**

```python
# Good: Mock the role (protocol/interface)
mock_notifier = mocker.Mock(spec=NotificationService)
service.process_order(mock_notifier)
mock_notifier.notify.assert_called_once_with(order)

# Bad: Mock the implementation
mock_email = mocker.Mock(spec=EmailClient)  # Too specific
```

**Don't Mock Values**

```python
# Good: Use real value objects
money = Money(100, "USD")
assert cart.total() == money

# Bad: Mock simple values
mock_money = mocker.Mock(spec=Money)  # Unnecessary
```

**Verify Interactions, Not State**

```python
# Good: Verify the right call was made
mock_repository.save.assert_called_once_with(entity)

# Less ideal: Check internal state
assert entity in repository.entities
```

---

## Test Anti-Patterns to Flag

### Critical Anti-Patterns

| Anti-Pattern               | Description                         | Fix                                |
| -------------------------- | ----------------------------------- | ---------------------------------- |
| **Missing Assertions**     | Test runs but verifies nothing      | Add meaningful assertions          |
| **Testing Framework Code** | Testing library/framework internals | Test your code, not theirs         |
| **Shared Mutable State**   | Tests affect each other             | Isolate setup, use fresh instances |
| **Production Data**        | Tests depend on real data           | Use fixtures or factories          |

### High Priority Anti-Patterns

| Anti-Pattern          | Description                          | Fix                           |
| --------------------- | ------------------------------------ | ----------------------------- |
| **Test-Per-Method**   | Mapping 1:1 with implementation      | Test behaviors, not methods   |
| **Excessive Mocking** | More mocks than real objects         | Simplify design, use fakes    |
| **Logic in Tests**    | Conditionals, loops in test code     | Keep tests linear and obvious |
| **Obscure Test**      | Can't understand what's being tested | Improve naming, simplify      |

### Medium Priority Anti-Patterns

| Anti-Pattern                | Description                    | Fix                           |
| --------------------------- | ------------------------------ | ----------------------------- |
| **Test Doubles Everywhere** | Never testing real integration | Add focused integration tests |
| **Assertion Roulette**      | Multiple unrelated assertions  | One concept per test          |
| **Long Tests**              | Hard to understand at a glance | Extract setup, split tests    |
| **Eager Test**              | Testing too many things        | Focus on one behavior         |

---

## Test Pain as Design Feedback

When tests are hard to write, it often indicates design problems:

| Test Difficulty             | Possible Design Issue             |
| --------------------------- | --------------------------------- |
| **Complex setup**           | Object has too many dependencies  |
| **Hard to mock**            | Interface too large, violates ISP |
| **Brittle tests**           | Implementation details exposed    |
| **Slow tests**              | Missing abstraction boundaries    |
| **Can't test in isolation** | Tight coupling between components |

---

## Coverage Verification

**CRITICAL**: This project requires 100% test coverage threshold.

When reviewing test changes, ALWAYS verify coverage:

```bash
uv run pytest --cov-report=term-missing
```

**Check the metrics `pytest-cov` reports** (branches and lines; the project
config already adds `--cov`, `--random-order`, `-vv`,
`--strict-markers`/`--strict-config` via `addopts`):

- Branches: Must be 100%
- Lines: Must be 100%

### Finding Format for Insufficient Coverage

**If coverage is below 100%**, report as HIGH severity:

```markdown
### Finding: Test coverage below 100%

- **Severity**: High
- **Category**: test
- **File**: path/to/file.py
- **Description**: Coverage is at X% (branches: X%, lines: X%). Project requires 100% coverage threshold.
- **Impact**: The pre-commit `pytest-check` hook and CI will fail. Untested code paths may contain bugs.
- **Fix**: Add tests for uncovered lines. Run `uv run pytest --cov-report=term-missing` to see gaps. Use `# pragma: nocover` / `# pragma: nobranch` ONLY for truly unreachable code (the established pattern in `nodes.py` and `parsers.py`).
```

**If 95-99% coverage**:

- Flag as HIGH severity finding
- List specific uncovered lines from the coverage report
- Suggest specific test cases for each gap
- Only suggest a `# pragma: nocover` if truly justified as unreachable

---

## Evaluation Output Format

For the Test Quality section of the review:

```markdown
### Test Quality

#### Classification Assessment

- **Unit Tests**: [Present/Missing] - [Assessment]
- **Integration Tests**: [Present/Missing] - [Assessment]
- **Acceptance Tests**: [Present/Missing] - [Assessment]

#### Test Desiderata Check

| Property      | Status    | Notes                  |
| ------------- | --------- | ---------------------- |
| Isolated      | Pass/Fail | [Specific observation] |
| Deterministic | Pass/Fail | [Specific observation] |
| Fast          | Pass/Fail | [Specific observation] |
| Readable      | Pass/Fail | [Specific observation] |
| Behavioral    | Pass/Fail | [Specific observation] |
| Specific      | Pass/Fail | [Specific observation] |

#### Coverage Report

- **Branches**: X%
- **Functions**: X%
- **Lines**: X%
- **Statements**: X%
- **Status**: [Pass/FAIL - see findings]

#### Mocking Assessment

- **Pattern**: [Appropriate/Over-mocked/Under-mocked]
- **Observations**: [Specific feedback on mocking usage]

#### Anti-Patterns Detected

[List any anti-patterns found, or "None detected"]

#### Design Feedback

[Any observations about design issues indicated by test difficulty, or "No design concerns"]
```

---

## Quick Checklist

For rapid evaluation, verify these essentials:

- [ ] Tests are behavioral (test what, not how)
- [ ] Tests are readable and self-documenting
- [ ] Tests are fast (no unnecessary I/O)
- [ ] Tests are deterministic (no flaky tests)
- [ ] Tests are isolated (no shared state)
- [ ] Tests are specific (clear failure messages)
- [ ] Mocking is appropriate (roles, not values)
- [ ] No critical anti-patterns present
- [ ] Coverage is 100% for all metrics
- [ ] Test pain signals are addressed or acknowledged

---

## Examples

### Good Test Pattern

```python
def test_it_should_notify_customer_when_order_ships(mocker) -> None:
    # Arrange
    notifier = mocker.Mock(spec=NotificationService)
    order = create_order(status="packed")
    service = OrderService(notifier)

    # Act
    service.ship_order(order)

    # Assert
    notifier.notify_shipped.assert_called_once_with(order)
    assert order.status == "shipped"
```

**Why it's good**:

- Clear behavior being tested (in the name)
- Minimal setup
- Tests role interaction (notifier)
- Verifiable outcome
- Follows AAA pattern (Arrange-Act-Assert)

### Bad Test Pattern

```python
db = RealDatabase()  # Shared module-level state
cache = RealCache()


def test_works() -> None:  # Vague name
    service = OrderService(db, cache)
    result = service.process({})  # What's being tested?
    assert result  # Weak assertion
```

**Why it's bad**:

- Shared mutable state (beforeAll with real instances)
- Unclear what behavior is tested
- No isolation (real DB, real cache)
- Weak assertion (truthy)
- Vague test name ("works")
