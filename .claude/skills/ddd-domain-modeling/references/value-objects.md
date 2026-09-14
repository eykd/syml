# Value Objects

Value objects are immutable, defined by their attributes, and have no identity.

## Table of Contents

- [Characteristics](#characteristics)
- [Patterns](#patterns)
- [Common Value Objects](#common-value-objects)
- [Equality and Comparison](#equality-and-comparison)
- [Testing Value Objects](#testing-value-objects)

## Characteristics

| Characteristic   | Description                                        |
| ---------------- | -------------------------------------------------- |
| Immutable        | State never changes after creation                 |
| No identity      | Two instances with same values are interchangeable |
| Self-validating  | Constructor rejects invalid values                 |
| Side-effect free | Methods return new instances                       |

## Patterns

### Basic Value Object

```python
@dataclasses.dataclass(frozen=True)
class Email:
    _value: str

    @classmethod
    def create(cls, value: str) -> 'Email':
        normalized = value.lower().strip()
        if not cls._is_valid(normalized):
            raise ValueError('Invalid email format')
        return cls(normalized)

    @staticmethod
    def _is_valid(email: str) -> bool:
        return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email))

    @property
    def value(self) -> str:
        return self._value

    @property
    def domain(self) -> str:
        return self._value.split('@')[1]
```

### Enum-Style Value Object

```python
class TaskStatus(enum.Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'

    @classmethod
    def pending(cls) -> 'TaskStatus':
        return cls.PENDING

    @classmethod
    def in_progress(cls) -> 'TaskStatus':
        return cls.IN_PROGRESS

    @classmethod
    def completed(cls) -> 'TaskStatus':
        return cls.COMPLETED

    @classmethod
    def from_string(cls, value: str) -> 'TaskStatus':
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f'Invalid status: {value}') from None

    @property
    def is_pending(self) -> bool:
        return self is TaskStatus.PENDING

    @property
    def is_completed(self) -> bool:
        return self is TaskStatus.COMPLETED

    def can_transition_to(self, target: 'TaskStatus') -> bool:
        if self is TaskStatus.PENDING:
            return target is TaskStatus.IN_PROGRESS
        if self is TaskStatus.IN_PROGRESS:
            return target is TaskStatus.COMPLETED or target is TaskStatus.PENDING
        return False  # Completed is terminal
```

### Composite Value Object

```python
@dataclasses.dataclass(frozen=True)
class Money:
    amount: float
    currency: str

    @classmethod
    def of(cls, amount: float, currency: str) -> 'Money':
        if not math.isfinite(amount):
            raise ValueError('Amount must be a finite number')
        if amount < 0:
            raise ValueError('Amount cannot be negative')
        if not re.match(r'^[A-Z]{3}$', currency):
            raise ValueError('Currency must be 3-letter ISO code')
        # Round to 2 decimal places
        return cls(round(amount, 2), currency)

    @classmethod
    def zero(cls, currency: str) -> 'Money':
        return cls.of(0, currency)

    def add(self, other: 'Money') -> 'Money':
        self._assert_same_currency(other)
        return Money.of(self.amount + other.amount, self.currency)

    def subtract(self, other: 'Money') -> 'Money':
        self._assert_same_currency(other)
        if other.amount > self.amount:
            raise ValueError('Cannot subtract: would result in negative amount')
        return Money.of(self.amount - other.amount, self.currency)

    def multiply(self, factor: float) -> 'Money':
        if factor < 0:
            raise ValueError('Factor cannot be negative')
        return Money.of(self.amount * factor, self.currency)

    def _assert_same_currency(self, other: 'Money') -> None:
        if self.currency != other.currency:
            raise ValueError(f'Currency mismatch: {self.currency} vs {other.currency}')

    def __str__(self) -> str:
        return f'{self.currency} {self.amount:.2f}'
```

## Common Value Objects

### ID Value Object

```python
@dataclasses.dataclass(frozen=True)
class TaskId:
    value: str

    @classmethod
    def create(cls) -> 'TaskId':
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'TaskId':
        if not value or len(value.strip()) == 0:
            raise ValueError('TaskId cannot be empty')
        return cls(value)
```

### Date Range Value Object

```python
@dataclasses.dataclass(frozen=True)
class DateRange:
    start: datetime.datetime
    end: datetime.datetime

    @classmethod
    def create(cls, start: datetime.datetime, end: datetime.datetime) -> 'DateRange':
        if end < start:
            raise ValueError('End date must be after start date')
        return cls(start, end)

    def contains(self, date: datetime.datetime) -> bool:
        return self.start <= date <= self.end

    def overlaps(self, other: 'DateRange') -> bool:
        return self.start <= other.end and self.end >= other.start

    @property
    def duration_in_days(self) -> int:
        return math.ceil((self.end - self.start).total_seconds() / (60 * 60 * 24))
```

### Address Value Object

```python
@dataclasses.dataclass(frozen=True)
class Address:
    street: str
    city: str
    postal_code: str
    country: str

    @classmethod
    def create(
        cls, *, street: str, city: str, postal_code: str, country: str
    ) -> 'Address':
        if not street or not street.strip():
            raise ValueError('Street is required')
        if not city or not city.strip():
            raise ValueError('City is required')
        if not postal_code or not postal_code.strip():
            raise ValueError('Postal code is required')
        if not country or not country.strip():
            raise ValueError('Country is required')

        return cls(
            street.strip(),
            city.strip(),
            postal_code.strip().upper(),
            country.strip(),
        )

    def format(self) -> str:
        return f'{self.street}, {self.city}, {self.postal_code}, {self.country}'
```

### Migration Table: Primitives → Value Objects

When refactoring existing code, identify primitives that should be value objects:

| Primitive Type       | Current Usage           | Value Object    | Validation                                          | Why Migrate                                                     |
| -------------------- | ------------------------ | ---------------- | ---------------------------------------------------- | ----------------------------------------------------------------- |
| `str`                | User ID / Task ID       | `UserId`        | UUID format, not empty                              | Type safety, prevents mixing IDs from different aggregates      |
| `str`                | Email address           | `Email`         | Email format, normalized (lowercase, trimmed)       | Consistent validation, normalization, domain queries            |
| `float`              | Money amount            | `Money`         | Non-negative, 2 decimal places, currency required   | Currency safety, arithmetic operations, display formatting      |
| `float`              | Percentage              | `Percentage`    | 0-100 range (or 0-1)                                | Range validation, consistent representation                     |
| `str`                | Phone number            | `PhoneNumber`   | Format validation, international format             | Consistent formatting, validation, comparison                   |
| `str`                | URL                     | `Url`           | Valid URL format, protocol required                 | Type safety, validation, manipulation methods                   |
| `str`                | Postal code             | `PostalCode`    | Format by country, normalized (uppercase)           | Country-specific validation, normalization                      |
| `int`                | Quantity                | `Quantity`      | Positive integer, unit of measure                   | Unit safety, arithmetic with units                               |
| `str`                | Color code              | `Color`         | Hex format (#RRGGBB), named colors                  | Validation, conversion to RGB/HSL                               |
| `datetime`           | Date range              | `DateRange`     | Start before end, no overlap validation             | Domain logic encapsulation, range operations                    |
| `str`                | Timestamps (stored)     | **Keep string** | UTC ISO 8601 format                                 | Portable datetime, no datetime object in domain (see below)     |
| `list[str]` / `set`  | Tags, categories        | `Tags`          | Unique, lowercase, no empty strings                 | Deduplication, normalization, domain operations                 |
| `tuple` (lat, long)  | Geographic coordinates  | `Coordinates`   | Valid latitude (-90 to 90), longitude (-180 to 180) | Validation, distance calculations, boundary checks              |
| `str`                | Enum-like (status, etc) | Domain enum     | Allowlist of valid values                           | Type safety, exhaustive match checks, state machine validation  |

### When NOT to Create Value Objects

**DON'T create value objects for:**

- Simple labels or display text (e.g., `first_name`, `description`)
- Intermediate calculation results
- Framework/library types (e.g., `datetime` for timestamps - use string instead)
- Data that has no invariants or business rules

**Example - Keep as primitives:**

```python
# CORRECT - Simple text, no business rules
@dataclasses.dataclass
class TaskProps:
    title: str  # Just a label
    description: str  # Free text


# WRONG - Unnecessary value object
class Title:
    # Overkill for simple text
    def __init__(self, value: str) -> None:
        self._value = value
```

### Refactoring Strategy

**Step 1: Identify primitives with business rules**

```python
# Before (primitive obsession)
@dataclasses.dataclass
class User:
    id: str  # What kind of ID?
    email: str  # Is it validated?
    balance: float  # What currency?
```

**Step 2: Create value objects**

```python
# UserId value object
@dataclasses.dataclass(frozen=True)
class UserId:
    value: str

    @classmethod
    def generate(cls) -> 'UserId':
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'UserId':
        if not cls._is_valid_uuid(value):
            raise ValidationError('Invalid UUID format')
        return cls(value)

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        return bool(
            re.match(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                value,
                re.IGNORECASE,
            )
        )

    def __str__(self) -> str:
        return self.value


# Email value object
@dataclasses.dataclass(frozen=True)
class Email:
    value: str

    @classmethod
    def create(cls, value: str) -> 'Email':
        normalized = value.lower().strip()
        if not cls._is_valid(normalized):
            raise ValidationError('Invalid email format')
        return cls(normalized)

    @staticmethod
    def _is_valid(email: str) -> bool:
        return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email))

    def __str__(self) -> str:
        return self.value


# Money value object
@dataclasses.dataclass(frozen=True)
class Money:
    amount: float
    currency: str

    @classmethod
    def of(cls, amount: float, currency: str) -> 'Money':
        if amount < 0:
            raise ValidationError('Amount cannot be negative')
        if not re.match(r'^[A-Z]{3}$', currency):
            raise ValidationError('Currency must be 3-letter ISO code')
        # Round to 2 decimal places for currency
        rounded = round(amount, 2)
        return cls(rounded, currency)

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValidationError('Cannot add different currencies')
        return Money.of(self.amount + other.amount, self.currency)

    def get_amount(self) -> float:
        return self.amount

    def get_currency(self) -> str:
        return self.currency
```

**Step 3: Update domain entity**

```python
# After (value objects)
@dataclasses.dataclass
class UserProps:
    id: UserId  # Self-documenting, validated
    email: Email  # Format enforced, normalized
    balance: Money  # Currency + amount, validated


class User:
    def __init__(self, id: UserId, email: Email, balance: Money) -> None:
        self._id = id
        self._email = email
        self._balance = balance

    @classmethod
    def create(cls, *, email: str, initial_balance: float = 0) -> 'User':
        return cls(
            UserId.generate(),
            Email.create(email),
            Money.of(initial_balance, 'USD'),
        )

    def change_email(self, new_email: str) -> None:
        self._email = Email.create(new_email)

    def add_funds(self, amount: Money) -> None:
        self._balance = self._balance.add(amount)

    def get_id(self) -> UserId:
        return self._id

    def get_email(self) -> Email:
        return self._email

    def get_balance(self) -> Money:
        return self._balance
```

**Step 4: Update repository mapping**

```python
# Repository handles string ↔ value object conversion
class SqliteUserRepository(UserRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, user: User) -> None:
        query = """
            INSERT INTO users (id, email, balance, currency)
            VALUES (?, ?, ?, ?)
        """

        self._conn.execute(
            query,
            (
                str(user.get_id()),  # UserId → str
                str(user.get_email()),  # Email → str
                user.get_balance().get_amount(),  # Money → float
                user.get_balance().get_currency(),  # Money → str
            ),
        )
        self._conn.commit()

    def find_by_id(self, user_id: UserId) -> User | None:
        row = self._conn.execute(
            'SELECT * FROM users WHERE id = ?', (str(user_id),)
        ).fetchone()

        if row is None:
            return None

        return User.reconstitute(
            id=UserId.from_string(row['id']),  # str → UserId
            email=Email.create(row['email']),  # str → Email
            balance=Money.of(row['balance'], row['currency']),  # float + str → Money
        )
```

### Special Case: Timestamps

**DON'T use `datetime` objects in domain entities**. Use UTC ISO 8601 strings instead.


```python
# WRONG - datetime object in domain
class Task:
    def __init__(self, id: TaskId, created_at: datetime.datetime) -> None:  # Timezone issues
        self._id = id
        self._created_at = created_at


# CORRECT - UTC string in domain
class Task:
    def __init__(self, id: TaskId, created_at: str) -> None:  # UTC ISO 8601
        self._id = id
        self._created_at = created_at

    @classmethod
    def create(cls, *, title: str) -> 'Task':
        return cls(TaskId.generate(), datetime.datetime.now(datetime.UTC).isoformat())

    def get_created_at(self) -> str:
        return self._created_at
```

## Equality and Comparison

Always give value objects value-based equality — a frozen `dataclass` provides `__eq__` for free from its fields:

```python
# By value comparison (generated by @dataclasses.dataclass(frozen=True))
money_a = Money.of(10, 'USD')
money_b = Money.of(10, 'USD')
assert money_a == money_b

# In collections
prices = [Money.of(10, 'USD'), Money.of(20, 'USD')]
target = Money.of(10, 'USD')
found = next((p for p in prices if p == target), None)  # Works
```

## Testing Value Objects

```python
class TestMoneyCreation:
    def test_creates_money_with_valid_amount_and_currency(self) -> None:
        money = Money.of(100, 'USD')
        assert money.amount == 100
        assert money.currency == 'USD'

    def test_rounds_to_2_decimal_places(self) -> None:
        money = Money.of(10.999, 'USD')
        assert money.amount == 11

    def test_rejects_negative_amounts(self) -> None:
        with pytest.raises(ValueError, match='cannot be negative'):
            Money.of(-10, 'USD')

    def test_rejects_invalid_currency_codes(self) -> None:
        with pytest.raises(ValueError, match='3-letter ISO'):
            Money.of(10, 'US')


class TestMoneyOperations:
    def test_adds_same_currency(self) -> None:
        a = Money.of(10, 'USD')
        b = Money.of(20, 'USD')
        assert a.add(b).amount == 30

    def test_rejects_adding_different_currencies(self) -> None:
        usd = Money.of(10, 'USD')
        eur = Money.of(10, 'EUR')
        with pytest.raises(ValueError, match='Currency mismatch'):
            usd.add(eur)


class TestMoneyEquality:
    def test_equals_same_value(self) -> None:
        a = Money.of(10, 'USD')
        b = Money.of(10, 'USD')
        assert a == b

    def test_not_equals_different_amount(self) -> None:
        a = Money.of(10, 'USD')
        b = Money.of(20, 'USD')
        assert a != b
```
