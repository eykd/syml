# Simplification Refactorings

## Inline Function

**When**: Function body is as clear as name, or just delegates.

**Steps**:

1. Check not polymorphic (not overridden)
2. Find all callers
3. Replace each call with body
4. Remove function
5. Test after each replacement

```python
# Before: Unnecessary indirection
def rating(driver: Driver) -> int:
    return 2 if more_than_five_late_deliveries(driver) else 1


def more_than_five_late_deliveries(driver: Driver) -> bool:
    return driver.number_of_late_deliveries > 5

# After
def rating(driver: Driver) -> int:
    return 2 if driver.number_of_late_deliveries > 5 else 1
```

## Inline Class

**When**: Class no longer justifies its existence after refactoring.

**Steps**:

1. Move all methods and fields to target class
2. Update references to use target
3. Remove empty class

```python
# Before: TrackingInformation has become trivial
class Shipment:
    @property
    def tracking_info(self) -> str:
        return self._tracking_information.display

    @property
    def tracking_information(self) -> TrackingInformation:
        return self._tracking_information


class TrackingInformation:
    @property
    def display(self) -> str:
        return f'{self.shipping_company}: {self.tracking_number}'

# After: Merged into Shipment
class Shipment:
    def __init__(self) -> None:
        self.shipping_company: str
        self.tracking_number: str

    @property
    def tracking_info(self) -> str:
        return f'{self.shipping_company}: {self.tracking_number}'
```

## Remove Dead Code

**When**: Code is never executed. Trust version control for history.

**Steps**:

1. Use tools/IDE to find unused code
2. Delete it
3. Test

```python
# Before: has_discount is never called
class Order:
    @property
    def total(self) -> float:
        return sum(i.price for i in self.items)

    # Dead code - delete it
    def has_discount(self) -> bool:
        return self.discount_code is not None

# After
class Order:
    @property
    def total(self) -> float:
        return sum(i.price for i in self.items)
```

## Collapse Hierarchy

**When**: Subclass and superclass are too similar.

**Steps**:

1. Choose which class to remove
2. Pull up or push down features to merge
3. Remove empty class
4. Update references

```python
# Before: Employee and Salesman have almost identical behavior
class Employee:
    name: str
    salary: float
    # ... many shared methods


class Salesman(Employee):
    @property
    def bonus(self) -> float:
        return self.sales * 0.1

# After: If all employees can have sales, collapse
class Employee:
    def __init__(self) -> None:
        self.name: str
        self.salary: float
        self.sales: float = 0

    @property
    def bonus(self) -> float:
        return self.sales * 0.1
```

## Remove Middle Man

**When**: Class mostly just delegates to another class.

**Steps**:

1. Expose delegate object
2. For each delegating method, adjust client to call delegate directly
3. Remove delegating methods

```python
# Before: Person just delegates to Department
class Person:
    @property
    def department(self) -> Department:
        return self._department

    @property
    def manager(self) -> Employee:
        return self._department.manager

    @property
    def budget(self) -> float:
        return self._department.budget

    @property
    def head_count(self) -> int:
        return self._department.head_count

# After: Let clients talk to Department directly
class Person:
    @property
    def department(self) -> Department:
        return self._department


# Client
manager = person.department.manager
```

## Replace Superclass/Subclass with Delegate

**When**: Inheritance isn't true is-a relationship; composition is better.

```python
# Before: Stack inherits List but isn't really a List
class Stack(list[T]):
    def push(self, item: T) -> None:
        self.append(item)

    def pop_item(self) -> T:
        return self.pop()

# After: Stack uses list via delegation
class Stack(Generic[T]):
    def __init__(self) -> None:
        self._storage: list[T] = []

    def push(self, item: T) -> None:
        self._storage.append(item)

    def pop_item(self) -> T:
        return self._storage.pop()
    # Note: list methods like sort(), insert() are NOT exposed
```

## Substitute Algorithm

**When**: Simpler algorithm becomes apparent.

**Steps**:

1. Ensure algorithm is in separate function
2. Prepare new algorithm
3. Test new algorithm independently
4. Replace old with new
5. Test

```python
# Before: Complex search
def find_person(people: list[Person]) -> Person | None:
    for p in people:
        if p.name == 'Don':
            return p
        if p.name == 'John':
            return p
        if p.name == 'Kent':
            return p
    return None

# After: Simpler approach
def find_person(people: list[Person]) -> Person | None:
    candidates = ('Don', 'John', 'Kent')
    return next((p for p in people if p.name in candidates), None)
```

## Signs of Speculative Generality

Remove these if not actually used:

- Abstract classes with only one subclass
- Unused parameters
- Methods/classes only called by tests
- Type parameters with only one instantiation
- Protocols/ABCs with a single implementation (and no planned extensions)
