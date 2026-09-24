# Extraction Refactorings

## Extract Function

**When**: Code block has clear purpose, appears multiple times, or function is too long.

**Steps**:

1. Create new function named after intent (what, not how)
2. Copy code to new function
3. Identify variables needed—pass as parameters
4. Replace original with function call
5. Test

```python
# Before
def print_owing(invoice: Invoice) -> None:
    outstanding = 0
    for o in invoice.orders:
        outstanding += o.amount

    print(f'Customer: {invoice.customer}')
    print(f'Amount: {outstanding}')

# After
def print_owing(invoice: Invoice) -> None:
    outstanding = calculate_outstanding(invoice)
    print_details(invoice, outstanding)


def calculate_outstanding(invoice: Invoice) -> float:
    return sum(o.amount for o in invoice.orders)


def print_details(invoice: Invoice, outstanding: float) -> None:
    print(f'Customer: {invoice.customer}')
    print(f'Amount: {outstanding}')
```

## Inline Function

**When**: Function body is as clear as its name, or function is simple delegation.

**Steps**:

1. Check function isn't polymorphic (not overridden)
2. Find all callers
3. Replace each call with function body
4. Remove function definition
5. Test after each replacement

```python
# Before
def get_rating(driver: Driver) -> int:
    return 2 if more_than_five_late_deliveries(driver) else 1


def more_than_five_late_deliveries(driver: Driver) -> bool:
    return driver.late_deliveries > 5

# After
def get_rating(driver: Driver) -> int:
    return 2 if driver.late_deliveries > 5 else 1
```

## Extract Variable

**When**: Complex expression is hard to understand.

**Steps**:

1. Ensure expression has no side effects
2. Declare variable with clear name
3. Assign expression to variable
4. Replace expression with variable reference

```python
# Before
return (
    order.quantity * order.item_price
    - max(0, order.quantity - 500) * order.item_price * 0.05
    + min(order.quantity * order.item_price * 0.1, 100)
)

# After
base_price = order.quantity * order.item_price
quantity_discount = max(0, order.quantity - 500) * order.item_price * 0.05
shipping = min(base_price * 0.1, 100)
return base_price - quantity_discount + shipping
```

## Inline Variable

**When**: Variable name doesn't add meaning beyond the expression.

**Steps**:

1. Check variable is assigned only once
2. Replace all references with expression
3. Remove declaration

```python
# Before
base_price = order.base_price
return base_price > 1000

# After
return order.base_price > 1000
```

## Replace Temp with Query

**When**: Temporary variable holds calculation that could be a function.

**Steps**:

1. Extract calculation into function
2. Replace temp references with function call
3. Remove temp declaration

```python
# Before
def price(order: Order) -> float:
    base_price = order.quantity * order.item_price
    if base_price > 1000:
        return base_price * 0.95
    return base_price * 0.98

# After
def price(order: Order) -> float:
    if base_price(order) > 1000:
        return base_price(order) * 0.95
    return base_price(order) * 0.98


def base_price(order: Order) -> float:
    return order.quantity * order.item_price
```
