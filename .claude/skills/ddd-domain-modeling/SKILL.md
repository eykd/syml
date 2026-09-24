---
name: ddd-domain-modeling
description: 'Use when: (1) building domain entities with validation, (2) creating value objects, (3) defining repository interfaces, (4) implementing domain services, (5) questions about DDD patterns or business logic encapsulation.'
---

# DDD Domain Modeling

Create domain models in pure Python with zero external dependencies.

## Core Principle

The domain layer contains **pure business logic only**:

- No framework imports
- No I/O operations in entities/value objects
- No database or HTTP concerns
- Validate invariants in constructors
- Dependencies point inward (infrastructure → application → domain)

## Directory Structure

```
src/domain/
├── entities/           # Aggregate roots and entities
│   ├── order.py
│   └── test_order.py
├── value_objects/      # Immutable value types
│   ├── money.py
│   └── email.py
├── services/           # Stateless domain logic
│   └── pricing_service.py
└── interfaces/         # Repository ports (interfaces only)
    └── order_repository.py
```

## Quick Reference

### Entity (3 parts)

```python
class Order:
    def __init__(self, props: OrderProps) -> None:
        self._props = props
        # Validate invariants here

    @classmethod
    def create(cls, input: CreateOrderInput) -> 'Order':
        ...  # validate + new

    @classmethod
    def reconstitute(cls, props: OrderProps) -> 'Order':
        ...  # from persistence

    # Getters + behavior methods that enforce rules
```

### Value Object

```python
@dataclasses.dataclass(frozen=True)
class Money:
    amount: float
    currency: str

    @classmethod
    def of(cls, amount: float, currency: str) -> 'Money':
        if amount < 0:
            raise ValueError('Amount cannot be negative')
        return cls(amount, currency)

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError('Currency mismatch')
        return Money.of(self.amount + other.amount, self.currency)
```

### Repository Interface

```python
# Domain layer - interface only
class OrderRepository(typing.Protocol):
    def find_by_id(self, order_id: str) -> Order | None: ...
    def save(self, order: Order) -> None: ...
```

### Domain Service

```python
# Stateless, operates on multiple entities/value objects
class PricingService:
    def calculate_total(self, items: list[LineItem], discounts: list[Discount]) -> Money:
        ...  # Complex calculation logic here
```

## Workflow

1. **Identify the concept**: Entity (has identity) or Value Object (defined by attributes)?
2. **Define invariants**: What rules must always be true?
3. **Choose pattern**: See detailed references below
4. **Write tests first**: Domain code is pure—test without mocks

## Detailed References

- **Entities with identity and lifecycle**: See [references/entities.md](references/entities.md)
- **Value Objects with validation**: See [references/value-objects.md](references/value-objects.md)
- **Repository interfaces (ports)**: See [references/repositories.md](references/repositories.md)
- **Domain services for complex logic**: See [references/domain-services.md](references/domain-services.md)

## Anti-Patterns to Avoid

| Anti-Pattern                      | Instead                                                            |
| --------------------------------- | ------------------------------------------------------------------ |
| `import sqlite3` in domain        | Define interface in domain, implement in infrastructure            |
| I/O in entity methods              | Keep entities synchronous; I/O belongs in repositories             |
| Exposing setters                  | Provide behavior methods: `order.add_item()` not `order.items = []` |
| Validation in application layer   | Validate in entity/value object constructors                       |
| Anemic domain model               | Put behavior with the data it operates on                          |
