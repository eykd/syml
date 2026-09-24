# Value Objects & Type Design

**Purpose**: Apply prefactoring principles when wrapping primitives, grouping data, and creating meaningful types.

## When to Use

- Creating new types for domain concepts
- Wrapping primitive values (strings, numbers)
- Grouping related parameters into objects
- Extracting magic numbers/strings to constants

## Core Principles

### Be Abstract All the Way

Never use primitives for domain concepts. Wrap them in meaningful types.

```python
# Bad: Primitives lose domain meaning
def create_user(email: str, age: int) -> None: ...


# Good: Domain types with validation
class Email:
    def __init__(self, value: str) -> None:
        if '@' not in value:
            raise InvalidEmailError(value)
        self._value = value

    def __str__(self) -> str:
        return self._value


class Age:
    def __init__(self, years: int) -> None:
        if years < 0 or years > 150:
            raise InvalidAgeError(years)
        self._years = years


def create_user(email: Email, age: Age) -> None: ...
```

### Clump Data

Group related values into cohesive objects to reduce cognitive load.

```python
# Bad: Parameter explosion
def place_order(
    street: str,
    city: str,
    zip_code: str,
    country: str,
    card_number: str,
    expiry: str,
    cvv: str,
) -> None: ...


# Good: Cohesive value objects
@dataclass(frozen=True)
class Address:
    street: str
    city: str
    zip_code: str
    country: str


@dataclass(frozen=True)
class PaymentDetails:
    card_number: str
    expiry: str
    cvv: str


def place_order(address: Address, payment: PaymentDetails) -> None: ...
```

### Never Let a Constant Slip

Use named constants for all meaningful values.

```python
# Bad: Magic numbers
if retry_count > 3:
    ...  # give up
if order.total > 1000:
    ...  # apply discount

# Good: Named constants
MAX_RETRY_ATTEMPTS = 3
BULK_ORDER_THRESHOLD = 1000

if retry_count > MAX_RETRY_ATTEMPTS:
    ...  # give up
if order.total > BULK_ORDER_THRESHOLD:
    ...  # apply discount
```

### Splitters Can Be Lumped

Start with fine-grained abstractions. It's easier to combine than to split.

```python
# Start specific, generalize later
class EmailNotification:
    ...  # email-specific


class SmsNotification:
    ...  # sms-specific


# Later, if needed, create common abstraction
class Notification(Protocol):
    async def send(self, recipient: Recipient, message: Message) -> None: ...
```

## Decision Matrix

| Situation             | Apply                   | Example                          |
| --------------------- | ----------------------- | -------------------------------- |
| String with format    | Be Abstract All the Way | `Email`, `Url`, `PhoneNumber`    |
| Number with units     | Be Abstract All the Way | `Money`, `Duration`, `Distance`  |
| Related parameters    | Clump Data              | `Address`, `DateRange`           |
| Literal value         | Named Constants         | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Uncertain granularity | Splitters Can Be Lumped | Start specific                   |

## Related References

- [collections.md](./collections.md): Domain collections with behavior
- [naming.md](./naming.md): Naming conventions for types
