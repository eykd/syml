# Encapsulation Refactorings

## Encapsulate Variable

**When**: Data is accessed widely; need to control access, add validation, or prepare for restructuring.

**Steps**:

1. Create getter and setter functions
2. Replace all direct references with function calls
3. Consider making data private
4. Test

```python
# Before
default_owner = Owner(first_name='Martin', last_name='Fowler')
spaceship.owner = default_owner

# After
_default_owner = Owner(first_name='Martin', last_name='Fowler')


def default_owner() -> Owner:
    return _default_owner


def set_default_owner(owner: Owner) -> None:
    global _default_owner
    _default_owner = owner


spaceship.owner = default_owner()
```

## Encapsulate Record

**When**: Data structures (dicts, plain records) need controlled access.

**Steps**:

1. Create class with private field for record
2. Provide methods to get/set values
3. Replace record usage with class
4. Consider making immutable

```python
# Before
organization = {'name': 'Acme', 'country': 'US'}
organization['name'] = 'New Name'

# After
class Organization:
    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    @property
    def name(self) -> str:
        return self._data['name']

    @name.setter
    def name(self, value: str) -> None:
        self._data['name'] = value

    @property
    def country(self) -> str:
        return self._data['country']
```

## Encapsulate Collection

**When**: Collection is exposed directly, allowing uncontrolled modification.

**Steps**:

1. Add methods to add/remove items
2. Return a read-only view or copy from the getter
3. Never return the mutable reference itself

```python
# Before
class Person:
    def __init__(self) -> None:
        self.courses: list[Course] = []


person.courses.append(new_course)

# After
class Person:
    def __init__(self) -> None:
        self._courses: list[Course] = []

    @property
    def courses(self) -> tuple[Course, ...]:
        return tuple(self._courses)

    def add_course(self, course: Course) -> None:
        self._courses.append(course)

    def remove_course(self, course: Course) -> None:
        if course in self._courses:
            self._courses.remove(course)
```

## Replace Primitive with Object

**When**: Primitive types (str, int) represent domain concepts.

**Steps**:

1. Create class for the value
2. Replace primitive with object
3. Move related behavior into class
4. Consider making immutable

```python
# Before
def delivery_date(order: Order) -> date:
    if order.priority == 'high':
        return add_days(order.placed_on, 1)
    return add_days(order.placed_on, 3)

# After
class Priority:
    _LEVELS = ('low', 'normal', 'high', 'rush')

    def __init__(self, value: str) -> None:
        if value not in self._LEVELS:
            raise ValueError(f'Invalid priority: {value}')
        self._value = value

    def higher_than(self, other: 'Priority') -> bool:
        return self._LEVELS.index(self._value) > self._LEVELS.index(other._value)
```

## Hide Delegate

**When**: Client navigates through one object to get to another (message chains).

**Steps**:

1. Create delegating method on server for each delegate method needed
2. Adjust client to call server
3. Remove client's knowledge of delegate

```python
# Before
manager = person.department.manager

# After (in Person class)
@property
def manager(self) -> Employee:
    return self.department.manager


# Client code
manager = person.manager
```

## Introduce Special Case (Null Object)

**When**: Same None / special case checks appear everywhere.

**Steps**:

1. Create special-case class implementing the same protocol
2. Return special-case instance instead of `None`
3. Move special-case behavior into special class

```python
# Before
def customer_name(site: Site) -> str:
    customer = site.customer
    if customer is None:
        return 'occupant'
    return customer.name

# After
class UnknownCustomer:
    @property
    def name(self) -> str:
        return 'occupant'

    @property
    def billing_plan(self) -> BillingPlan:
        return BillingPlan.basic()


def customer_name(site: Site) -> str:
    return site.customer.name  # Works for real and unknown customers
```
