# Architecture & System Design

**Purpose**: Apply prefactoring principles when designing system structure, modules, and boundaries.

## When to Use

- Creating new modules or packages
- Defining system boundaries or layer organization
- Making architectural decisions about component relationships
- Choosing between inheritance and composition

## Core Principles

### Well-Defined Interfaces

Define interfaces before implementation. Document preconditions, postconditions, and side effects.

```python
class UserRepository(Protocol):
    """Repository protocol defines contract, not implementation."""

    def find_by_id(self, id: UserId) -> User:
        """Return the user; raises NotFoundError if the user doesn't exist."""
        ...

    def save(self, user: User) -> User:
        """Persist the user and return it with a generated ID."""
        ...
```

### Decomposition & Modularity

Split systems into cohesive, loosely-coupled modules. Each module has one clear responsibility.

```python
# Good: Separate modules by domain concern
# src/users/domain/        - User entities, value objects
# src/users/application/   - Use cases
# src/users/infrastructure/- Repository implementations
# src/orders/domain/       - Order entities (separate bounded context)
```

### Separation of Concerns

Each module addresses one concern. Orthogonal concerns live in separate modules.

```python
# Separate concerns: validation, persistence, notification
class CreateUserUseCase:
    def __init__(
        self,
        validator: UserValidator,  # Validation concern
        repository: UserRepository,  # Persistence concern
        notifier: UserNotifier,  # Notification concern
    ) -> None:
        self._validator = validator
        self._repository = repository
        self._notifier = notifier
```

### Hierarchy & Layers

Dependencies flow in one direction: higher layers depend on lower layers.

```python
# Layer hierarchy (dependencies flow down)
# Handlers    -> Use Cases    -> Domain      -> (nothing)
# (adapters)  -> (application) -> (entities)

# Use case depends on domain, not vice versa
class ProcessOrderUseCase:
    def execute(self, request: ProcessOrderRequest) -> Order:
        order = Order.create(request)  # Domain has no use case dependency
        return self._repository.save(order)
```

### Packaging

Components that change together should be packaged together.

```python
# Group by feature/domain, not by type
# Good:
# src/orders/order_entity.py
# src/orders/order_repository.py
# src/orders/create_order_use_case.py

# Bad:
# src/entities/order_entity.py
# src/repositories/order_repository.py
# src/usecases/create_order_use_case.py
```

### Think in Interfaces, Not Inheritance

Prefer composition and interfaces over inheritance hierarchies.

```python
# Bad: Rigid inheritance
class Animal:
    def move(self) -> None:
        pass


class Bird(Animal):
    def fly(self) -> None:
        pass


class Penguin(Bird):
    pass  # Can't fly!


# Good: Composition via protocols
class Movable(Protocol):
    def move(self) -> None: ...


class Flyable(Protocol):
    def fly(self) -> None: ...


class Penguin:
    def move(self) -> None:
        ...  # waddle
```

## Decision Matrix

| Situation             | Apply                    | Example                      |
| --------------------- | ------------------------ | ---------------------------- |
| New module            | Decomposition, Packaging | Group related files together |
| API boundary          | Well-Defined Interfaces  | Document contracts           |
| Cross-cutting concern | Separation of Concerns   | Extract to separate module   |
| Class hierarchy       | Think in Interfaces      | Prefer composition           |
| Dependency direction  | Hierarchy                | Higher depends on lower      |

## Related References

- [abstraction.md](./abstraction.md): Type-level design decisions
- [interfaces.md](./interfaces.md): Contract design and validation
