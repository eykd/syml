# Domain Collections & Method Placement

**Purpose**: Apply prefactoring principles for collections with behavior and proper method placement.

## When to Use

- Working with arrays/lists that have domain meaning
- Deciding where methods should live
- Encapsulating aggregate operations
- Preventing feature envy anti-pattern

## Core Principles

### Collections with Domain Behavior

Wrap collections when they have domain-specific operations.

```python
# Bad: Raw array with scattered logic
items: list[OrderItem] = []
total = sum(item.price for item in items)
has_discount = len(items) > 10

# Good: Domain collection with behavior
class OrderItems:
    def __init__(self, items: list[OrderItem]) -> None:
        self._items = items

    def total(self) -> Money:
        return sum((item.price for item in self._items), Money.zero())

    def has_discount(self) -> bool:
        return len(self._items) > BULK_DISCOUNT_THRESHOLD

    def is_empty(self) -> bool:
        return len(self._items) == 0
```

### Place Methods by Need

Methods belong where their data lives. Avoid feature envy.

```python
# Bad: Feature envy - method uses another object's data
class OrderPrinter:
    def print(self, order: Order) -> str:
        return f'{order.id}: {len(order.items)} items, ${order.total}'


class OrderValidator:
    def is_valid(self, order: Order) -> bool:
        return len(order.items) > 0 and order.total > 0


# Good: Methods on the object with the data
class Order:
    def __str__(self) -> str:
        return f'{self.id}: {len(self.items)} items, ${self.total}'

    def is_valid(self) -> bool:
        return len(self.items) > 0 and self.total > 0
```

### Static Methods for Non-Instance Operations

If a method doesn't need instance data, it shouldn't be a member.

```python
# Bad: Instance method that doesn't use instance data
class DateUtils:
    def format_date(self, date: datetime) -> str:
        return date.date().isoformat()


# Good: Static or module-level function
def format_date(date: datetime) -> str:
    return date.date().isoformat()


# Or as a static method
class DateUtils:
    @staticmethod
    def format_date(date: datetime) -> str:
        return date.date().isoformat()
```

## Decision Matrix

| Situation                       | Apply                  | Action                         |
| ------------------------------- | ---------------------- | ------------------------------ |
| Array with operations           | Collection Wrapper     | Create domain collection class |
| Method uses other object's data | Place Methods by Need  | Move to data owner             |
| Method doesn't use `this`       | Static/Module Function | Extract to static or function  |
| Multiple methods on same data   | Domain Object          | Group into cohesive class      |

## Collection Wrapper Checklist

When creating a domain collection, consider:

- [ ] Does it encapsulate the underlying array/map?
- [ ] Does it provide domain-specific query methods?
- [ ] Does it enforce invariants (e.g., non-empty)?
- [ ] Does it hide implementation details?

```python
class UserGroup:
    def __init__(self, users: list[User]) -> None:
        if len(users) == 0:
            raise EmptyGroupError()
        self._users = users

    @classmethod
    def create(cls, users: list[User]) -> 'UserGroup':
        return cls(users)

    def find_by_email(self, email: Email) -> User | None:
        return next((u for u in self._users if u.email == email), None)

    def active_users(self) -> 'UserGroup':
        return UserGroup([u for u in self._users if u.is_active])
```

## Related References

- [value-objects.md](./value-objects.md): Creating domain types
- [separation.md](./separation.md): Separating concerns in code
