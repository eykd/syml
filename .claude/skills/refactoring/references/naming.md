# Naming Refactorings

## Change Function Declaration (Rename Function)

**When**: Function name doesn't clearly communicate purpose.

**Steps** (Simple):

1. Change function name in declaration
2. Update all call sites
3. Test

**Steps** (Migration for published APIs):

1. Create new function with better name
2. Have old function delegate to new
3. Migrate callers gradually
4. Remove old function

```python
# Before
def circum(radius: float) -> float:
    return 2 * math.pi * radius

# After
def circumference(radius: float) -> float:
    return 2 * math.pi * radius
```

## Rename Variable

**When**: Variable name is unclear or misleading.

**Steps**:

1. If widely used, consider Encapsulate Variable first
2. Change name in declaration
3. Update all references
4. Use IDE automated renaming when available

```python
# Before
a = height * width

# After
area = height * width
```

## Rename Field

**When**: Field name doesn't match current understanding of data.

**Steps**:

1. If record has limited scope, rename directly
2. Otherwise, use Encapsulate Record first
3. Rename private field
4. Adjust accessors

```python
# Before
class Organization(TypedDict):
    name: str
    ctry: str

# After
class Organization(TypedDict):
    name: str
    country: str
```

## Comments → Better Names

**When**: Comments describe what code does (not why).

Comments are often a sign of unclear code. Instead of documenting unclear code, make it clear through better naming.

```python
# Before
# Check if customer is eligible for discount
if customer.age > 65 or customer.membership_years > 10:
    # Apply senior or loyalty discount
    total = total * 0.9

# After
is_eligible_for_discount = customer.age > 65 or customer.membership_years > 10
if is_eligible_for_discount:
    total = apply_discount(total, LOYALTY_DISCOUNT_RATE)

# OR even better: Extract Function
if is_eligible_for_discount(customer):
    total = apply_discount(total, LOYALTY_DISCOUNT_RATE)
```

## Good Naming Principles

1. **Use domain language** — Match terms stakeholders use (e.g. `SymlNode`, `incorporate_node`, not generic `Item`/`process`)
2. **Reveal intent** — Name after what, not how
3. **Be specific** — `customer_count` not `data`
4. **Avoid abbreviations** — `circumference` not `circum`
5. **Keep comments for "why"** — Code should explain "what"

| Bad Name    | Good Name          | Reason                   |
| ----------- | ------------------- | ------------------------ |
| `d`         | `elapsed_days`       | Reveals what it measures |
| `list_`     | `customers`          | Reveals domain meaning   |
| `flag`      | `is_active`          | Reveals purpose          |
| `temp`      | `subtotal`           | Reveals business concept |
| `do_stuff()` | `calculate_tax()`   | Reveals operation        |
| `data`      | `user_profile`       | Reveals content type     |
