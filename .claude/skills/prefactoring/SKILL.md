---
name: prefactoring
description: 'Use when: (1) designing systems/modules, (2) creating types/abstractions, (3) naming and structuring code, (4) defining interfaces/contracts, (5) planning error handling.'
---

# Prefactoring Principles

Apply Ken Pugh's prefactoring principles proactively during design and implementation.

## Decision Tree

### Need to design system structure?

**When**: Creating modules, defining boundaries, making architectural decisions
**Go to**: [references/architecture.md](./references/architecture.md)

### Need to create domain types?

**When**: Wrapping primitives, extracting constants, grouping related data
**Go to**: [references/value-objects.md](./references/value-objects.md)

### Need to work with collections?

**When**: Arrays with domain behavior, deciding where methods belong
**Go to**: [references/collections.md](./references/collections.md)

### Need to name things?

**When**: Naming functions/classes, making code self-documenting
**Go to**: [references/naming.md](./references/naming.md)

### Need to eliminate duplication?

**When**: DRY violations, separating policy from implementation
**Go to**: [references/separation.md](./references/separation.md)

### Need to define API contracts?

**When**: Public APIs, validation, designing for testability
**Go to**: [references/contracts.md](./references/contracts.md)

### Need to handle errors?

**When**: Error strategies, user messages, resilient systems
**Go to**: [references/error-handling.md](./references/error-handling.md)

## Quick Reference

### Before Writing Code

1. Does this already exist? (Don't reinvent the wheel)
2. What invariants must hold? (Define contracts)
3. Can I test this? (Design for testability)
4. What should this be named? (Use domain language)

### Creating Types

- Wrap primitives: `Email`, `Money`, `UserId` not `string`, `number`
- Group related data: Parameter objects, value objects
- Split fine, lump later (easier to combine than split)

## Anti-Patterns

| Anti-Pattern           | Principle Violated        | Fix                       |
| ---------------------- | ------------------------- | ------------------------- |
| Magic numbers/strings  | Never let a constant slip | Extract named constants   |
| Primitive obsession    | Be abstract all the way   | Create domain types       |
| God class              | Separation of concerns    | Split by responsibility   |
| Feature envy           | Place methods by need     | Move method to data owner |
| Silent failure         | Never be silent           | Always report errors      |
| Premature optimization | Don't speed until...      | Make it right first       |

## Quick Example

```python
# Before: Primitive obsession, magic numbers
def process_order(email: str, amount: float) -> None:
    if amount > 1000:
        pass  # discount logic


# After: Domain types, named constants
BULK_ORDER_THRESHOLD = 1000


class Money:
    def __init__(self, cents: int) -> None:
        self._cents = cents

    def exceeds_threshold(self, threshold: int) -> bool:
        return self._cents > threshold * 100


class Email:
    def __init__(self, value: str) -> None:
        if '@' not in value:
            raise ValueError('Invalid email')
        self._value = value


def process_order(email: Email, amount: Money) -> None:
    if amount.exceeds_threshold(BULK_ORDER_THRESHOLD):
        ...
```

## Cross-References

- **[ddd-domain-modeling](../ddd-domain-modeling/SKILL.md)**: Value objects, entities, aggregates
- **[clean-architecture-validator](../clean-architecture-validator/SKILL.md)**: Layer boundaries, dependency rules
- **[pytest-unit-testing](../pytest-unit-testing/SKILL.md)**: Test-driven development, test design

## Reference Files

- [references/architecture.md](./references/architecture.md): System design, modularity, hierarchy
- [references/value-objects.md](./references/value-objects.md): Domain types, constants, data grouping
- [references/collections.md](./references/collections.md): Domain collections, method placement
- [references/naming.md](./references/naming.md): Ubiquitous language, self-documenting code
- [references/separation.md](./references/separation.md): DRY, policy/implementation separation
- [references/contracts.md](./references/contracts.md): API contracts, validation, testability
- [references/error-handling.md](./references/error-handling.md): Error strategies, Result type
