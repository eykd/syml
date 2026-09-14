# Domain Services

Domain services contain business logic that doesn't naturally fit within a single entity or value object.

## Table of Contents

- [When to Use Domain Services](#when-to-use-domain-services)
- [Characteristics](#characteristics)
- [Patterns](#patterns)
- [Testing Domain Services](#testing-domain-services)

## When to Use Domain Services

Use a domain service when the operation:

- Involves multiple entities or aggregates
- Requires business logic that doesn't belong to any single entity
- Implements a domain concept that is a "verb" rather than a "noun"
- Needs to enforce cross-entity invariants

| Scenario                              | Solution                                    |
| -------------------------------------- | -------------------------------------------- |
| Calculate order total from line items | Entity method: `order.calculate_total()`     |
| Check if user can afford a purchase   | Domain service: `PaymentEligibilityService` |
| Transfer funds between accounts       | Domain service: `FundsTransferService`      |
| Validate an email format              | Value object: `Email.create()`              |

## Characteristics

Domain services are:

- **Stateless**: No instance state, operate purely on inputs
- **Pure**: No side effects, same inputs → same outputs
- **Framework-free**: No database, HTTP, or infrastructure dependencies
- **Synchronous**: No I/O operations (those belong in application layer)

```python
# Good: Pure domain service
class PricingService:
    def calculate_discount(
        self, items: list[LineItem], customer_tier: CustomerTier
    ) -> Money:
        ...  # Pure calculation logic


# Bad: Has infrastructure concerns
class PricingService:
    def __init__(self, db: Database) -> None:  # Infrastructure dependency
        self._db = db

    def calculate_discount(self, customer_id: str) -> Money:  # I/O bound
        customer = self._db.find_customer(customer_id)
        # ...
```

## Patterns

### Calculation Service

```python
# src/domain/services/pricing_service.py
from ..value_objects.money import Money
from ..entities.line_item import LineItem
from ..value_objects.discount import Discount


class PricingService:
    def calculate_subtotal(self, items: list[LineItem]) -> Money:
        if len(items) == 0:
            return Money.zero('USD')

        total = Money.zero(items[0].price.currency)
        for item in items:
            total = total.add(item.price.multiply(item.quantity))
        return total

    def apply_discounts(self, subtotal: Money, discounts: list[Discount]) -> Money:
        total = subtotal

        # Sort by type: percentage discounts first, then fixed
        sorted_discounts = sorted(
            discounts, key=lambda d: 0 if d.type == 'percentage' else 1
        )

        for discount in sorted_discounts:
            if discount.type == 'percentage':
                reduction = total.multiply(discount.value / 100)
                total = total.subtract(reduction)
            else:
                total = total.subtract(Money.of(discount.value, total.currency))

        # Never go below zero
        return Money.zero(total.currency) if total.amount < 0 else total

    def calculate_tax(self, amount: Money, tax_rate: float) -> Money:
        return amount.multiply(tax_rate / 100)
```

### Validation Service

```python
# src/domain/services/order_validation_service.py
from ..entities.order import Order
from ..entities.customer import Customer
from ..value_objects.money import Money


@dataclasses.dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]


class OrderValidationService:
    def validate_order(self, order: Order, customer: Customer) -> ValidationResult:
        errors: list[str] = []

        # Business rule: Customer must be active
        if not customer.is_active:
            errors.append('Customer account is not active')

        # Business rule: Order value within customer's credit limit
        if order.total.amount > customer.credit_limit.amount:
            errors.append('Order exceeds customer credit limit')

        # Business rule: Minimum order value
        minimum_order = Money.of(10, order.total.currency)
        if order.total.amount < minimum_order.amount:
            errors.append('Order must be at least $10')

        # Business rule: No more than 100 items per order
        if order.item_count > 100:
            errors.append('Order cannot exceed 100 items')

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

### Policy Service

```python
# src/domain/services/shipping_policy_service.py
from ..entities.order import Order
from ..value_objects.address import Address
from ..value_objects.money import Money


@dataclasses.dataclass
class ShippingOption:
    name: str
    cost: Money
    estimated_days: int


class ShippingPolicyService:
    FREE_SHIPPING_THRESHOLD = Money.of(50, 'USD')

    def get_available_options(
        self, order: Order, destination: Address
    ) -> list[ShippingOption]:
        options: list[ShippingOption] = []
        currency = order.total.currency

        # Standard shipping always available
        options.append(
            ShippingOption(
                name='Standard',
                cost=self._calculate_standard_cost(order, destination),
                estimated_days=self._get_standard_delivery_days(destination),
            )
        )

        # Express available for orders under 50lbs
        if order.total_weight < 50:
            options.append(
                ShippingOption(name='Express', cost=Money.of(15.99, currency), estimated_days=2)
            )

        # Overnight for domestic only
        if destination.country == 'US':
            options.append(
                ShippingOption(name='Overnight', cost=Money.of(29.99, currency), estimated_days=1)
            )

        return options

    def _calculate_standard_cost(self, order: Order, destination: Address) -> Money:
        # Free shipping over threshold
        if order.total.amount >= self.FREE_SHIPPING_THRESHOLD.amount:
            return Money.zero(order.total.currency)

        # Base cost + weight surcharge
        base_cost = 5.99 if destination.country == 'US' else 14.99
        weight_surcharge = max(0, (order.total_weight - 5) * 0.5)

        return Money.of(base_cost + weight_surcharge, order.total.currency)

    def _get_standard_delivery_days(self, destination: Address) -> int:
        return 5 if destination.country == 'US' else 14
```

### Allocation/Distribution Service

```python
# src/domain/services/inventory_allocation_service.py
from ..entities.order_item import OrderItem
from ..entities.warehouse_stock import WarehouseStock


@dataclasses.dataclass
class Allocation:
    warehouse_id: str
    quantity: int


@dataclasses.dataclass
class Shortfall:
    product_id: str
    quantity: int


@dataclasses.dataclass
class AllocationResult:
    allocations: dict[str, list[Allocation]]
    unallocated: list[Shortfall]


class InventoryAllocationService:
    def allocate_stock(
        self, items: list[OrderItem], warehouse_stocks: list[WarehouseStock]
    ) -> AllocationResult:
        allocations: dict[str, list[Allocation]] = {}
        unallocated: list[Shortfall] = []

        for item in items:
            product_allocations: list[Allocation] = []
            remaining = item.quantity

            # Sort warehouses by available stock (highest first)
            sorted_stocks = sorted(
                (ws for ws in warehouse_stocks if ws.product_id == item.product_id),
                key=lambda ws: ws.available,
                reverse=True,
            )

            for stock in sorted_stocks:
                if remaining <= 0:
                    break

                allocate = min(remaining, stock.available)
                if allocate > 0:
                    product_allocations.append(
                        Allocation(warehouse_id=stock.warehouse_id, quantity=allocate)
                    )
                    remaining -= allocate

            if len(product_allocations) > 0:
                allocations[item.product_id] = product_allocations

            if remaining > 0:
                unallocated.append(Shortfall(product_id=item.product_id, quantity=remaining))

        return AllocationResult(allocations=allocations, unallocated=unallocated)
```

## Testing Domain Services

Domain services are pure functions—test without mocks:

```python
class TestPricingService:
    def setup_method(self) -> None:
        self.service = PricingService()

    class TestCalculateSubtotal:
        def setup_method(self) -> None:
            self.service = PricingService()

        def test_sums_all_line_items(self) -> None:
            items = [
                create_line_item(price=Money.of(10, 'USD'), quantity=2),
                create_line_item(price=Money.of(5, 'USD'), quantity=3),
            ]

            result = self.service.calculate_subtotal(items)

            assert result.amount == 35  # (10*2) + (5*3)

        def test_returns_zero_for_empty_items(self) -> None:
            result = self.service.calculate_subtotal([])
            assert result.amount == 0

    class TestApplyDiscounts:
        def setup_method(self) -> None:
            self.service = PricingService()

        def test_applies_percentage_discount(self) -> None:
            subtotal = Money.of(100, 'USD')
            discounts = [Discount(type='percentage', value=10)]

            result = self.service.apply_discounts(subtotal, discounts)

            assert result.amount == 90

        def test_applies_fixed_discount(self) -> None:
            subtotal = Money.of(100, 'USD')
            discounts = [Discount(type='fixed', value=15)]

            result = self.service.apply_discounts(subtotal, discounts)

            assert result.amount == 85

        def test_applies_percentage_before_fixed(self) -> None:
            subtotal = Money.of(100, 'USD')
            discounts = [
                Discount(type='fixed', value=10),
                Discount(type='percentage', value=10),
            ]

            result = self.service.apply_discounts(subtotal, discounts)

            # 100 - 10% = 90, then 90 - 10 = 80
            assert result.amount == 80

        def test_never_returns_negative(self) -> None:
            subtotal = Money.of(10, 'USD')
            discounts = [Discount(type='fixed', value=50)]

            result = self.service.apply_discounts(subtotal, discounts)

            assert result.amount == 0


# Test helper
def create_line_item(*, price: Money, quantity: int) -> LineItem:
    return LineItem.create(product_id='prod-1', price=price, quantity=quantity)
```

### Integration with Use Cases

```python
# src/application/use_cases/place_order.py
from src.domain.services.pricing_service import PricingService
from src.domain.services.shipping_policy_service import ShippingPolicyService
from src.domain.services.order_validation_service import OrderValidationService


class PlaceOrder:
    def __init__(
        self,
        order_repository: OrderRepository,
        customer_repository: CustomerRepository,
        pricing_service: PricingService,
        shipping_service: ShippingPolicyService,
        validation_service: OrderValidationService,
    ) -> None:
        self._order_repository = order_repository
        self._customer_repository = customer_repository
        self._pricing_service = pricing_service
        self._shipping_service = shipping_service
        self._validation_service = validation_service

    def execute(self, request: PlaceOrderRequest) -> PlaceOrderResult:
        customer = self._customer_repository.find_by_id(request.customer_id)
        if customer is None:
            raise ValueError('Customer not found')

        # Use domain services for business logic
        subtotal = self._pricing_service.calculate_subtotal(request.items)
        after_discounts = self._pricing_service.apply_discounts(subtotal, request.discounts)
        shipping = self._shipping_service.get_available_options(
            Order(total=after_discounts, items=request.items),
            request.shipping_address,
        )[0]  # Use first option

        order = Order.create(
            customer_id=customer.id,
            items=request.items,
            subtotal=subtotal,
            discounts=after_discounts,
            shipping=shipping.cost,
            total=after_discounts.add(shipping.cost),
        )

        # Validate using domain service
        validation = self._validation_service.validate_order(order, customer)
        if not validation.is_valid:
            return PlaceOrderResult(success=False, errors=validation.errors)

        self._order_repository.save(order)
        return PlaceOrderResult(success=True, order_id=order.id)
```
