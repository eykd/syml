# Separation & DRY Principles

**Purpose**: Apply prefactoring principles for eliminating duplication and separating concerns.

## When to Use

- Deciding between duplication and abstraction
- Separating business rules from technical logic
- Implementing varying algorithms
- Structuring complex logic

## Core Principles

### Don't Repeat Yourself

Every piece of knowledge has a single, authoritative representation.

```python
# Bad: Duplicated validation logic
def create_user(email: str) -> None:
    if '@' not in email:
        raise ValueError('Invalid')


def update_email(email: str) -> None:
    if '@' not in email:
        raise ValueError('Invalid')


# Good: Single source of truth
class Email:
    def __init__(self, value: str) -> None:
        if '@' not in value:
            raise InvalidEmailError(value)
        self._value = value


def create_user(email: Email) -> None: ...
def update_email(email: Email) -> None: ...
```

### Separate Policy from Implementation

Keep the "what" separate from the "how" for flexibility and clarity.

```python
# Bad: Policy mixed with implementation
def calculate_discount(order: Order) -> float:
    if order.total > 1000:
        return order.total * 0.1
    if len(order.items) > 10:
        return order.total * 0.05
    return 0


# Good: Policy separate from implementation
class DiscountPolicy(Protocol):
    def applies(self, order: Order) -> bool: ...
    def calculate(self, order: Order) -> Money: ...


class BulkOrderDiscount:
    def applies(self, order: Order) -> bool:
        return order.total.exceeds(BULK_THRESHOLD)

    def calculate(self, order: Order) -> Money:
        return order.total.multiply(0.1)


class DiscountCalculator:
    def __init__(self, policies: list[DiscountPolicy]) -> None:
        self._policies = policies

    def calculate(self, order: Order) -> Money:
        applicable = next((p for p in self._policies if p.applies(order)), None)
        return applicable.calculate(order) if applicable else Money.zero()
```

### Avoid Premature Generalization

Solve the specific problem first. Generalize when patterns emerge.

```python
# Bad: Premature abstraction before second use case
class DataProcessor(Protocol[T, R]):
    def process(self, input: T) -> R: ...
    def validate(self, input: T) -> bool: ...
    def transform(self, input: T) -> T: ...


# Good: Solve specific problem first
def process_user_registration(data: RegistrationData) -> User:
    ...  # Implement specifically for this use case


# Later, when you have 2-3 similar cases, THEN abstract
def process_order_submission(data: OrderData) -> Order:
    ...  # If pattern emerges, consider shared abstraction
```

### Adapt a Prefactoring Attitude

Eliminate duplication before it occurs. Look for patterns during design.

```python
# Before implementing feature #2, check if it shares logic with feature #1
# If so, extract shared logic BEFORE implementing #2

# Example: Before adding SMS notifications alongside email
class NotificationChannel(Protocol):
    async def send(self, recipient: Recipient, message: Message) -> None: ...


# Now both implementations follow same pattern
class EmailChannel:
    ...  # NotificationChannel implementation


class SmsChannel:
    ...  # NotificationChannel implementation
```

## Decision Matrix

| Situation                          | Apply                          | Action                     |
| ---------------------------------- | ------------------------------ | -------------------------- |
| Logic in multiple places           | DRY                            | Extract to single location |
| Algorithm can vary                 | Policy/Implementation          | Use strategy pattern       |
| Building first implementation      | Avoid Premature Generalization | Keep specific              |
| About to implement similar feature | Prefactoring Attitude          | Extract pattern first      |

## When to Extract vs. Duplicate

```
Rule of Three:
1st occurrence: Just write it
2nd occurrence: Note the duplication
3rd occurrence: Extract the abstraction
```

## Related References

- [naming.md](./naming.md): Naming extracted abstractions
- [architecture.md](./architecture.md): Module-level separation
