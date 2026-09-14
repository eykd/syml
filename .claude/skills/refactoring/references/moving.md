# Moving Refactorings

## Move Function

**When**: Function uses elements from another context more than its own (Feature Envy).

**Steps**:

1. Examine function's context usage
2. Copy function to target context
3. Adjust for new location (rename, change parameters)
4. Set up delegation from old to new
5. Test, then remove old or leave as delegation

```python
# Before: track_summary uses total_distance more than its own class
class GPS:
    def track_summary(self, points: list[Point]) -> Summary:
        total_distance = self._calculate_distance(points)
        pace = total_distance / len(points)
        return Summary(distance=total_distance, pace=pace)

    def _calculate_distance(self, points: list[Point]) -> float:
        return sum(
            points[i].distance_to(points[i - 1]) for i in range(1, len(points))
        )

# After: Move to where data lives
class Track:
    def __init__(self, points: list[Point]) -> None:
        self.points = points

    @property
    def total_distance(self) -> float:
        return sum(
            self.points[i].distance_to(self.points[i - 1])
            for i in range(1, len(self.points))
        )

    @property
    def pace(self) -> float:
        return self.total_distance / len(self.points)
```

## Move Field

**When**: Field is used more by another class, or data structures are too coupled.

**Steps**:

1. If public, use Encapsulate Variable first
2. Create field in target
3. Adjust references to use target field
4. Remove source field

```python
# Before: discount relates more to CustomerContract
class Customer:
    discount_rate: float
    contract: CustomerContract

# After
class Customer:
    contract: CustomerContract

    @property
    def discount_rate(self) -> float:
        return self.contract.discount_rate


class CustomerContract:
    discount_rate: float
```

## Move Statements into Function

**When**: Same code appears in multiple callers of a function.

**Steps**:

1. If statements aren't adjacent, use Slide Statements first
2. Copy statements into function body
3. Test
4. Remove statements from callers

```python
# Before
def render_person(person: Person) -> str:
    result = [f'<p>{person.name}</p>']
    result.append(render_photo(person.photo))
    result.append(f'<p>title: {person.photo.title}</p>')
    return '\n'.join(result)

# After: title rendering moved into render_photo
def render_photo(photo: Photo) -> str:
    return '\n'.join([f'<img src="{photo.url}">', f'<p>title: {photo.title}</p>'])
```

## Move Statements to Callers

**When**: Function does too much; some behavior should vary by caller.

**Steps**:

1. Use Slide Statements to move varying code to function exit
2. Copy varying code to each caller
3. Remove from function

```python
# Before: emit_photo_data always outputs location, but not all callers want it
def emit_photo_data(photo: Photo) -> str:
    return f'<p>title: {photo.title}</p>\n<p>location: {photo.location}</p>'

# After
def emit_photo_data(photo: Photo) -> str:
    return f'<p>title: {photo.title}</p>'


# Callers that need location add it themselves
print(emit_photo_data(photo) + f'\n<p>location: {photo.location}</p>')
```

## Slide Statements

**When**: Related code is scattered; group for Extract Function or clarity.

**Steps**:

1. Identify target position
2. Check for dependencies that would break if moved
3. Move code to target
4. Test

```python
# Before
pricing_plan = retrieve_pricing_plan()
order = retrieve_order()
charge: float
charge_per_unit = pricing_plan.unit

# After: Group pricing-related code
pricing_plan = retrieve_pricing_plan()
charge_per_unit = pricing_plan.unit
order = retrieve_order()
charge: float
```

## Replace Inline Code with Function Call

**When**: Code duplicates logic that exists in a library or elsewhere.

```python
# Before
has_discount = False
for customer in customers:
    if customer.is_premium:
        has_discount = True
        break

# After
has_discount = any(c.is_premium for c in customers)
```

## Split Loop

**When**: Loop does multiple unrelated things.

**Steps**:

1. Copy loop
2. Remove different operations from each copy
3. Test
4. Consider Extract Function on each loop

```python
# Before
youngest = float('inf')
total_salary = 0
for p in people:
    if p.age < youngest:
        youngest = p.age
    total_salary += p.salary

# After
youngest = float('inf')
for p in people:
    if p.age < youngest:
        youngest = p.age

total_salary = 0
for p in people:
    total_salary += p.salary

# Even better: Use built-ins
youngest = min(p.age for p in people)
total_salary = sum(p.salary for p in people)
```
