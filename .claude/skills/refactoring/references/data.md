# Data Refactorings

## Split Variable

**When**: Variable is assigned multiple times for different purposes (except loop variables and accumulators).

**Steps**:

1. Change variable name at first declaration
2. Change references up to next assignment
3. Declare new variable at next assignment
4. Repeat for each assignment

```python
# Before: temp used for two different things
temp = 2 * (height + width)
print(temp)  # perimeter
temp = height * width
print(temp)  # area

# After: Separate variables for separate purposes
perimeter = 2 * (height + width)
print(perimeter)
area = height * width
print(area)
```

## Replace Derived Variable with Query

**When**: Variable can be calculated from other data; eliminates mutable state.

**Steps**:

1. Identify all update points
2. Create function to calculate value
3. Use assertion to verify calculation matches
4. Replace variable reads with function call
5. Remove variable and updates

```python
# Before: discounted_total updated manually
class ProductionPlan:
    def __init__(self) -> None:
        self._production: float = 0
        self._discounted_total: float = 0

    def add_adjustment(self, amount: float) -> None:
        self._production += amount
        self._discounted_total += amount * 0.9

    @property
    def discounted_total(self) -> float:
        return self._discounted_total

# After: Calculate when needed
class ProductionPlan:
    def __init__(self) -> None:
        self._production: float = 0

    def add_adjustment(self, amount: float) -> None:
        self._production += amount

    @property
    def discounted_total(self) -> float:
        return self._production * 0.9
```

## Change Reference to Value

**When**: Object should have value semantics (compared by content, not identity).

**Steps**:

1. Check object is/can be immutable
2. Create `__eq__` based on fields (or use a frozen dataclass, which gets this for free)
3. Remove setter methods
4. Consider making fields read-only

```python
# Before: TelephoneNumber compared by reference
class Person:
    def __init__(self) -> None:
        self._telephone_number: TelephoneNumber

    @property
    def office_area_code(self) -> str: ...

    @office_area_code.setter
    def office_area_code(self, value: str) -> None:
        self._telephone_number.area_code = value

# After: Immutable value object
@dataclass(frozen=True)
class TelephoneNumber:
    area_code: str
    number: str


class Person:
    def __init__(self) -> None:
        self._telephone_number: TelephoneNumber

    @property
    def office_area_code(self) -> str: ...

    @office_area_code.setter
    def office_area_code(self, value: str) -> None:
        self._telephone_number = TelephoneNumber(value, self._telephone_number.number)
```

## Change Value to Reference

**When**: Need to share single instance so updates are seen everywhere.

**Steps**:

1. Create repository for instances
2. Ensure constructor can look up correct instance
3. Change factory to return reference from repository

```python
# Before: Each Order has its own Customer copy
class Order:
    def __init__(self, data: OrderData) -> None:
        self._customer = Customer(data.customer_id)

# After: Orders share Customer references
customer_repository: dict[str, Customer] = {}


def find_customer(id: str) -> Customer:
    if id not in customer_repository:
        customer_repository[id] = Customer(id)
    return customer_repository[id]


class Order:
    def __init__(self, data: OrderData) -> None:
        self._customer = find_customer(data.customer_id)
```

## Replace Loop with Pipeline

**When**: Loop processes collection; pipeline operations are clearer.

**Steps**:

1. Create variable for loop result
2. Convert each loop operation to a comprehension or generator expression
3. Remove loop

```python
# Before
names = []
for person in people:
    if person.job == 'programmer':
        names.append(person.name)

# After
names = [p.name for p in people if p.job == 'programmer']
```

## Common Pipeline Operations

| Loop Pattern                | Pipeline Operation                  |
| ---------------------------- | ------------------------------------ |
| Filter items                  | `[x for x in xs if pred(x)]`         |
| Transform items                | `[f(x) for x in xs]`                 |
| Find single item               | `next((x for x in xs if pred(x)), None)` |
| Check if any match             | `any(pred(x) for x in xs)`           |
| Check if all match             | `all(pred(x) for x in xs)`           |
| Accumulate to single value     | `functools.reduce(f, xs, initial)`   |
| Flatten nested lists           | `[y for x in xs for y in x]`         |
