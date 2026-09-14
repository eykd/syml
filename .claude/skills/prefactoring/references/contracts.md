# Interface Contracts & Validation

**Purpose**: Apply prefactoring principles when defining APIs, validating inputs, and designing for testability.

## When to Use

- Defining public APIs or contracts
- Implementing input validation at boundaries
- Writing tests that verify behavior
- Designing testable components

## Core Principles

### Create Interface Contracts

Document and enforce preconditions, postconditions, and invariants.

```python
class TransferService(Protocol):
    """Transfer money between accounts.

    Preconditions:
        Both accounts must exist and be active.
        The source account must have a sufficient balance.
    Postconditions:
        source.balance = source.balance - amount
        target.balance = target.balance + amount
    Raises:
        InsufficientFundsError: if the balance is too low.
        AccountNotFoundError: if an account doesn't exist.
    """

    def transfer(self, source: AccountId, target: AccountId, amount: Money) -> None: ...
```

### Validate, Validate, Validate

Validate at every system boundary. Fail fast with clear error messages.

```python
class CreateUserHandler:
    async def handle(self, request: object) -> Response:
        # Validate at entry point
        validated = self.validate(request)
        if not validated.success:
            return Response.json({'errors': validated.errors}, status=400)

        # Domain types are already valid
        email = Email(validated.data.email)
        user = await self.use_case.execute(email)
        return Response.json(user)
```

### Test the Interface, Not the Implementation

Test contracts, not internal details. Enable refactoring without breaking tests.

```python
# Bad: Tests implementation details
def test_should_call_repository_save_with_correct_sql() -> None:
    repository.save(user)
    mock_db.query.assert_called_with('INSERT INTO...')


# Good: Tests contract
async def test_should_persist_user_and_return_with_id() -> None:
    user = User.create(email=Email('test@example.com'))
    saved = await repository.save(user)

    assert saved.id is not None
    retrieved = await repository.find_by_id(saved.id)
    assert retrieved is not None
    assert retrieved.email == user.email
```

### Build Flexibility for Testing

Design with dependency injection and clear interfaces.

```python
# Testable design: dependencies injected
class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        payment_gateway: PaymentGateway,
        notifier: OrderNotifier,
    ) -> None:
        self._repository = repository
        self._payment_gateway = payment_gateway
        self._notifier = notifier


# In tests: inject test doubles
service = OrderService(
    InMemoryOrderRepository(),
    MockPaymentGateway(),
    SpyOrderNotifier(),
)
```

## Decision Matrix

| Situation            | Apply               | Example                        |
| -------------------- | ------------------- | ------------------------------ |
| Public API method    | Interface Contracts | Document pre/postconditions    |
| External input       | Validate            | Check at system boundary       |
| Writing tests        | Test Interface      | Verify contract, not internals |
| Complex dependencies | Build Flexibility   | Use dependency injection       |

## Related References

- [error-handling.md](./error-handling.md): Error strategies and messaging
- [architecture.md](./architecture.md): Interface design at module level
