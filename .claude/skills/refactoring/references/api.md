# API Refactorings

## Introduce Parameter Object

**When**: Same parameters travel together; group reveals deeper abstraction.

**Steps**:

1. Create class/type for grouped parameters
2. Add parameter of new type
3. Replace individual parameters
4. Consider moving behavior into new class

```python
# Before: Range parameters appear together everywhere
def amount_invoiced_in(start: date, end: date) -> float: ...
def amount_received_in(start: date, end: date) -> float: ...
def amount_overdue_in(start: date, end: date) -> float: ...

# After: DateRange reveals domain concept
@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end


def amount_invoiced_in(range: DateRange) -> float: ...
def amount_received_in(range: DateRange) -> float: ...
def amount_overdue_in(range: DateRange) -> float: ...
```

## Remove Flag Argument

**When**: Boolean/enum parameter changes function behavior; separate functions are clearer.

**Steps**:

1. Create explicit function for each flag value
2. Replace callers with explicit version
3. Remove original or leave as wrapper

```python
# Before: What does True mean?
set_dimension(name, 10, True)

# After: Intent is clear
set_width(10)
set_height(10)

# Implementation
def set_width(value: float) -> None:
    set_dimension('width', value)


def set_height(value: float) -> None:
    set_dimension('height', value)
```

## Preserve Whole Object

**When**: Passing multiple values extracted from single object.

**Steps**:

1. Add parameter for whole object
2. Adjust function to extract values
3. Update callers to pass whole object
4. Consider if dependency is acceptable

```python
# Before: Extracting values just to pass them
low = room.days_temp_range.low
high = room.days_temp_range.high
if plan.within_range(low, high):
    ...

# After: Pass the whole object
if plan.within_range(room.days_temp_range):
    ...


class HeatingPlan:
    def within_range(self, range: TempRange) -> bool:
        return (
            range.low >= self._temperature_range.low
            and range.high <= self._temperature_range.high
        )
```

## Replace Parameter with Query

**When**: Parameter can be determined from other parameters or context.

**Steps**:

1. Extract calculation if needed
2. Replace parameter references with calculation
3. Remove parameter from declaration and calls

```python
# Before: quantity can be derived
def final_price(self, base_price: float, discount_level: int, quantity: int) -> float:
    return base_price * (1 - self.discount_for(discount_level, quantity))

# After: Calculate quantity internally
def final_price(self, base_price: float, discount_level: int) -> float:
    quantity = self.order.quantity
    return base_price * (1 - self.discount_for(discount_level, quantity))
```

## Replace Query with Parameter

**When**: Need to reduce dependencies or make function more flexible.

**Steps**:

1. Extract calculation if needed
2. Add parameter to function
3. Replace internal query with parameter
4. Update callers to pass value

```python
# Before: Function depends on global thermostat
class HeatingPlan:
    @property
    def target_temperature(self) -> float:
        if thermostat.selected_temperature > self._max:
            return self._max
        if thermostat.selected_temperature < self._min:
            return self._min
        return thermostat.selected_temperature

# After: Caller provides temperature
class HeatingPlan:
    def target_temperature(self, selected_temp: float) -> float:
        if selected_temp > self._max:
            return self._max
        if selected_temp < self._min:
            return self._min
        return selected_temp


# Caller
plan.target_temperature(thermostat.selected_temperature)
```

## Separate Query from Modifier

**When**: Function returns value AND has side effects.

**Steps**:

1. Copy function for query version
2. Remove side effects from query
3. Remove return from modifier
4. Replace callers: query for value, modifier for effect

```python
# Before: get_total_and_send_bill does two things
def get_total_and_send_bill() -> float:
    total = sum(o.amount for o in orders)
    send_bill(total)
    return total

# After: Separate concerns
def get_total() -> float:
    return sum(o.amount for o in orders)


def send_bill() -> None:
    send_bill_email(get_total())


# Caller
total = get_total()
send_bill()
```

## Remove Setting Method

**When**: Field should be set only at construction time.

**Steps**:

1. Check field is only set in constructor
2. Add to constructor parameters if needed
3. Remove setter method
4. Make field read-only

```python
# Before: id can be changed after creation
class Person:
    def __init__(self) -> None:
        self._id: str = ''

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str) -> None:
        self._id = value

# After: Immutable after construction
@dataclass(frozen=True)
class Person:
    id: str
```
