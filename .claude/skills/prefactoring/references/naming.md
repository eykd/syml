# Naming & Code Communication

**Purpose**: Apply prefactoring principles for clear naming, self-documenting code, and explicit intent.

## When to Use

- Naming functions, classes, or variables
- Making code self-documenting
- Choosing between implicit and explicit behavior
- Deciding whether to build or reuse

## Core Principles

### A Rose by Any Other Name

Each concept gets one clear, consistent name from the domain language.

```python
# Bad: Inconsistent naming
def get_user(): ...
def fetch_customer(): ...  # Same concept, different name
def retrieve_person(): ...  # Same concept, different name

# Good: Consistent ubiquitous language
def find_user(): ...
def find_user_by_id(): ...
def find_user_by_email(): ...
```

### Communicate with Your Code

Code should communicate intent without requiring comments.

```python
# Bad: Comment explains unclear code
# Check if user can access the resource
if user.role == 'admin' or user.id == resource.owner_id:
    ...

# Good: Self-documenting code
is_admin = user.has_role(Role.ADMIN)
is_owner = resource.is_owned_by(user)
if is_admin or is_owner:
    ...
```

### Explicitness Beats Implicitness

State intent clearly. Avoid magic behavior.

```python
# Bad: Implicit behavior
def process_order(order: Order, options: dict | None = None) -> None:
    should_notify = (options or {}).get('notify', True)  # Implicit default


# Good: Explicit parameters
@dataclass
class OrderOptions:
    notify: bool


def process_order(order: Order, options: OrderOptions) -> None:
    if options.notify:
        ...
```

### Don't Reinvent the Wheel

Use existing solutions before creating new ones.

```python
# Bad: Custom date formatting
def format_date(date: datetime) -> str:
    return f'{date.month}/{date.day}/{date.year}'


# Good: Use the standard library
formatted = date.strftime('%m/%d/%Y')
```

## Decision Matrix

| Situation                     | Apply                 | Action                   |
| ----------------------------- | --------------------- | ------------------------ |
| Same concept, different names | Ubiquitous Language   | Standardize naming       |
| Code needs explanation        | Communicate with Code | Rename for clarity       |
| Magic defaults                | Explicitness          | Make parameters explicit |
| Standard problem              | Don't Reinvent        | Use existing library     |

## Naming Checklist

When naming, ask:

- [ ] Does it use domain language? (not technical jargon)
- [ ] Is it consistent with similar concepts?
- [ ] Does it reveal intent? (not implementation)
- [ ] Is it searchable? (avoid abbreviations)

```python
# Domain language examples
class Order:  # Not: DataRecord, Entity
    pass


class Money:  # Not: NumberWrapper, AmountValue
    pass


def place_order():  # Not: process_data, handle_request
    pass
```

## Related References

- [separation.md](./separation.md): Code structure and DRY
- [value-objects.md](./value-objects.md): Naming domain types
