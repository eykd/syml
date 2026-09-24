# Polymorphism Refactorings

## Replace Conditional with Polymorphism

**When**: Same switch/if-else checks type in multiple places.

**Steps**:

1. Create class hierarchy if needed
2. Use factory for object creation
3. Move conditional logic into polymorphic method
4. Replace conditional with method call

```python
# Before: match on type in multiple places
def plumage(bird: Bird) -> str:
    match bird.type:
        case 'european_swallow':
            return 'average'
        case 'african_swallow':
            return 'tired' if bird.number_of_coconuts > 2 else 'average'
        case 'norwegian_blue_parrot':
            return 'scorched' if bird.voltage > 100 else 'beautiful'
        case _:
            return 'unknown'


def air_speed(bird: Bird) -> float:
    match bird.type:
        case 'european_swallow':
            return 35
        case 'african_swallow':
            return 40 - 2 * bird.number_of_coconuts
        case 'norwegian_blue_parrot':
            return 0 if bird.is_nailed else 10 + bird.voltage / 10
        case _:
            return 0

# After: Polymorphic classes
class Bird(ABC):
    @property
    @abstractmethod
    def plumage(self) -> str: ...

    @property
    @abstractmethod
    def air_speed(self) -> float: ...


class EuropeanSwallow(Bird):
    @property
    def plumage(self) -> str:
        return 'average'

    @property
    def air_speed(self) -> float:
        return 35


class AfricanSwallow(Bird):
    def __init__(self, number_of_coconuts: int) -> None:
        self.number_of_coconuts = number_of_coconuts

    @property
    def plumage(self) -> str:
        return 'tired' if self.number_of_coconuts > 2 else 'average'

    @property
    def air_speed(self) -> float:
        return 40 - 2 * self.number_of_coconuts


class NorwegianBlueParrot(Bird):
    def __init__(self, voltage: float, is_nailed: bool) -> None:
        self.voltage = voltage
        self.is_nailed = is_nailed

    @property
    def plumage(self) -> str:
        return 'scorched' if self.voltage > 100 else 'beautiful'

    @property
    def air_speed(self) -> float:
        return 0 if self.is_nailed else 10 + self.voltage / 10


# Factory
def create_bird(data: BirdData) -> Bird:
    match data.type:
        case 'european_swallow':
            return EuropeanSwallow()
        case 'african_swallow':
            return AfricanSwallow(data.number_of_coconuts)
        case 'norwegian_blue_parrot':
            return NorwegianBlueParrot(data.voltage, data.is_nailed)
        case _:
            raise ValueError(f'Unknown bird type: {data.type}')
```

## Decompose Conditional

**When**: Complex condition obscures intent; first step toward polymorphism.

**Steps**:

1. Extract condition into function with clear name
2. Extract then-branch into function
3. Extract else-branch into function

```python
# Before
if value < SUMMER_START or value > SUMMER_END:
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate

# After
if is_summer(value):
    charge = summer_charge(quantity)
else:
    charge = winter_charge(quantity)


def is_summer(value: date) -> bool:
    return SUMMER_START <= value <= SUMMER_END


def summer_charge(quantity: float) -> float:
    return quantity * summer_rate


def winter_charge(quantity: float) -> float:
    return quantity * winter_rate + winter_service_charge
```

## Replace Type Code with Subclasses

**When**: Type code affects behavior; enables polymorphism.

**Steps**:

1. Self-encapsulate type code if not already
2. Create subclass for each type code value
3. Create factory to return appropriate subclass
4. Replace type code checks with polymorphic methods

```python
# Before: Type code as field
class Employee:
    def __init__(self, type: Literal['engineer', 'salesman', 'manager']) -> None:
        self.type = type

    @property
    def bonus(self) -> float:
        match self.type:
            case 'engineer':
                return self.salary * 0.1
            case 'salesman':
                return self.sales * 0.15
            case 'manager':
                return self.salary * 0.2 + self.team_bonus

# After: Type hierarchy
class Employee(ABC):
    @property
    @abstractmethod
    def bonus(self) -> float: ...


class Engineer(Employee):
    @property
    def bonus(self) -> float:
        return self.salary * 0.1


class Salesman(Employee):
    @property
    def bonus(self) -> float:
        return self.sales * 0.15


class Manager(Employee):
    @property
    def bonus(self) -> float:
        return self.salary * 0.2 + self.team_bonus


def create_employee(type: str, data: EmployeeData) -> Employee:
    match type:
        case 'engineer':
            return Engineer(data)
        case 'salesman':
            return Salesman(data)
        case 'manager':
            return Manager(data)
        case _:
            raise ValueError(f'Unknown type: {type}')
```

## Introduce Assertion

**When**: Assumptions about state should be explicit.

**Steps**:

1. Identify assumption that must be true
2. Add assertion checking assumption
3. Use for invariants, not user input validation

```python
# Before: Implicit assumption about discount
def apply_discount(price: float, discount_rate: float) -> float:
    return price - price * discount_rate

# After: Explicit assertion
def apply_discount(price: float, discount_rate: float) -> float:
    assert 0 <= discount_rate <= 1, f'Discount rate must be 0-1, got {discount_rate}'
    return price - price * discount_rate
```

## When NOT to Use Polymorphism

- **One-off conditional**: If the branch appears only once, leave it
- **Simple cases**: Don't create hierarchy for 2-3 simple cases
- **External data**: Type info comes from JSON/DB, keep factory `match`/`if`
- **Performance critical**: Virtual dispatch has overhead
