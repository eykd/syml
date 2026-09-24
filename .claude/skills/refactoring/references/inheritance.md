# Inheritance Refactorings

## Pull Up Method

**When**: Methods in subclasses do the same thing.

**Steps**:

1. Check methods are identical (or make them so)
2. Check method signatures match
3. Create method in superclass
4. Remove from subclasses
5. Test

```python
# Before: Duplicate in subclasses
class Employee(ABC):
    @property
    @abstractmethod
    def annual_cost(self) -> float: ...


class Engineer(Employee):
    @property
    def annual_cost(self) -> float:
        return self.monthly_cost * 12


class Salesman(Employee):
    @property
    def annual_cost(self) -> float:
        return self.monthly_cost * 12

# After: Pull up to superclass
class Employee(ABC):
    @property
    @abstractmethod
    def monthly_cost(self) -> float: ...

    @property
    def annual_cost(self) -> float:
        return self.monthly_cost * 12
```

## Pull Up Field

**When**: Subclasses have same field.

**Steps**:

1. Check fields are used similarly
2. Create field in superclass
3. Remove from subclasses

```python
# Before
class Engineer(Employee):
    name: str


class Salesman(Employee):
    name: str

# After
class Employee(ABC):
    name: str


class Engineer(Employee): ...
class Salesman(Employee): ...
```

## Pull Up Constructor Body

**When**: Subclass constructors have common code.

**Steps**:

1. Create superclass constructor if needed
2. Move common statements to superclass
3. Call `super().__init__()` from subclasses

```python
# Before: Repeated initialization
class Employee:
    name: str


class Engineer(Employee):
    def __init__(self, name: str, specialization: str) -> None:
        self.name = name
        self.specialization = specialization


class Manager(Employee):
    def __init__(self, name: str, department: str) -> None:
        self.name = name
        self.department = department

# After
class Employee:
    def __init__(self, name: str) -> None:
        self.name = name


class Engineer(Employee):
    def __init__(self, name: str, specialization: str) -> None:
        super().__init__(name)
        self.specialization = specialization


class Manager(Employee):
    def __init__(self, name: str, department: str) -> None:
        super().__init__(name)
        self.department = department
```

## Push Down Method

**When**: Method only relevant to specific subclass.

**Steps**:

1. Copy method to subclass(es) that need it
2. Remove from superclass

```python
# Before: Only Salesman uses quota
class Employee:
    @property
    def quota(self) -> float:
        return self._quota

# After
class Employee: ...


class Salesman(Employee):
    @property
    def quota(self) -> float:
        return self._quota
```

## Push Down Field

**When**: Field only used by specific subclass.

```python
# Before
class Employee:
    quota: float  # Only used by Salesman

# After
class Employee: ...


class Salesman(Employee):
    quota: float
```

## Replace Subclass with Delegate

**When**: Inheritance doesn't fit; need more flexibility.

**Why**:

- Can only inherit once
- Inheritance couples tightly
- Subclass relationship isn't true is-a

**Steps**:

1. Create delegate class for subclass behavior
2. Add delegate field to superclass
3. Move subclass methods to delegate
4. Replace subclass with factory that configures delegate

```python
# Before: Booking inheritance limits flexibility
class Booking:
    def __init__(self, show: Show, date: date) -> None:
        self.show = show
        self.date = date

    @property
    def has_talkback(self) -> bool:
        return False

    @property
    def base_price(self) -> float:
        return self.show.price


class PremiumBooking(Booking):
    def __init__(self, show: Show, date: date, extras: Extras) -> None:
        super().__init__(show, date)
        self.extras = extras

    @property
    def has_talkback(self) -> bool:
        return self.show.has_talkback and not self.is_peak_day

    @property
    def base_price(self) -> float:
        return round(super().base_price + self.extras.premium_fee)

# After: Delegate provides flexibility
class Booking:
    def __init__(self, show: Show, date: date) -> None:
        self.show = show
        self.date = date
        self._premium_delegate: PremiumBookingDelegate | None = None

    def be_premium(self, extras: Extras) -> None:
        self._premium_delegate = PremiumBookingDelegate(self, extras)

    @property
    def has_talkback(self) -> bool:
        if self._premium_delegate is None:
            return False
        return self._premium_delegate.has_talkback

    @property
    def base_price(self) -> float:
        base = self.show.price
        if self._premium_delegate is None:
            return base
        return self._premium_delegate.adjust_price(base)


class PremiumBookingDelegate:
    def __init__(self, host: Booking, extras: Extras) -> None:
        self.host = host
        self.extras = extras

    @property
    def has_talkback(self) -> bool:
        return self.host.show.has_talkback and not self.host.is_peak_day

    def adjust_price(self, base: float) -> float:
        return round(base + self.extras.premium_fee)
```

## Extract Superclass

**When**: Classes share features; hierarchy is appropriate.

**Steps**:

1. Create empty superclass
2. Make classes extend it
3. Pull up common features one by one

```python
# Before: Department and Employee share features
class Employee:
    def __init__(self, name: str, annual_cost: float) -> None:
        self.name = name
        self.annual_cost = annual_cost

    @property
    def monthly_spend(self) -> float:
        return self.annual_cost / 12


class Department:
    def __init__(self, name: str, staff: list[Employee]) -> None:
        self.name = name
        self.staff = staff

    @property
    def total_annual_cost(self) -> float:
        return sum(e.annual_cost for e in self.staff)

    @property
    def monthly_spend(self) -> float:
        return self.total_annual_cost / 12

# After
class Party(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @property
    @abstractmethod
    def annual_cost(self) -> float: ...

    @property
    def monthly_spend(self) -> float:
        return self.annual_cost / 12


class Employee(Party):
    def __init__(self, name: str, annual_cost: float) -> None:
        super().__init__(name)
        self._annual_cost = annual_cost

    @property
    def annual_cost(self) -> float:
        return self._annual_cost


class Department(Party):
    def __init__(self, name: str, staff: list[Employee]) -> None:
        super().__init__(name)
        self.staff = staff

    @property
    def annual_cost(self) -> float:
        return sum(e.annual_cost for e in self.staff)
```

## When to Prefer Delegation Over Inheritance

| Use Inheritance When               | Use Delegation When                 |
| ----------------------------------- | ------------------------------------ |
| True is-a relationship             | Has-a or uses-a relationship        |
| Subclass uses most of superclass   | Only needs part of interface        |
| Subclass is truly a specialization | Need runtime flexibility            |
| Hierarchy is stable                | Behavior might change independently |
| Only need single inheritance       | Need multiple "parents"             |
