# Repository Interfaces

Repository interfaces define the contract for persistence in the domain layer. Implementation lives in infrastructure.

## Table of Contents

- [The Ports and Adapters Pattern](#the-ports-and-adapters-pattern)
- [Interface Design](#interface-design)
- [Common Repository Methods](#common-repository-methods)
- [Specification Pattern](#specification-pattern)
- [Implementation Guidelines](#implementation-guidelines)

## The Ports and Adapters Pattern

```
┌─────────────────────────────────────────────────────┐
│                    Domain Layer                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  class TaskRepository(Protocol) (PORT)      │    │
│  │    find_by_id(task_id: str) -> Task | None  │    │
│  │    save(task: Task) -> None                 │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                         ▲
                         │ implements
┌─────────────────────────────────────────────────────┐
│                Infrastructure Layer                  │
│  ┌─────────────────────────────────────────────┐    │
│  │  class SqliteTaskRepository (ADAPTER)       │    │
│  │    def __init__(self, conn: sqlite3.Connection) │
│  │    def find_by_id(task_id) -> Task | None   │    │
│  │    def save(task) -> None                   │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Key Rule**: Domain layer defines the interface. Infrastructure layer provides the implementation.

## Interface Design

### Basic Repository Interface

```python
# src/domain/interfaces/task_repository.py
import typing

from ..entities.task import Task


class TaskRepository(typing.Protocol):
    def find_by_id(self, task_id: str) -> Task | None: ...
    def find_all(self) -> list[Task]: ...
    def save(self, task: Task) -> None: ...
    def delete(self, task_id: str) -> None: ...
```

### Repository with Query Methods

```python
# src/domain/interfaces/order_repository.py
import typing

from ..entities.order import Order
from ..value_objects.order_status import OrderStatus
from ..value_objects.date_range import DateRange


class OrderRepository(typing.Protocol):
    # Core CRUD
    def find_by_id(self, order_id: str) -> Order | None: ...
    def save(self, order: Order) -> None: ...
    def delete(self, order_id: str) -> None: ...

    # Domain-specific queries
    def find_by_customer_id(self, customer_id: str) -> list[Order]: ...
    def find_by_status(self, status: OrderStatus) -> list[Order]: ...
    def find_by_date_range(self, date_range: DateRange) -> list[Order]: ...

    # Aggregate queries
    def count_by_status(self, status: OrderStatus) -> int: ...
    def exists_by_id(self, order_id: str) -> bool: ...
```

### Repository with Pagination

```python
T = typing.TypeVar('T')


@dataclasses.dataclass
class Page(typing.Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@dataclasses.dataclass
class PageRequest:
    page: int
    page_size: int
    sort_by: str | None = None
    sort_order: typing.Literal['asc', 'desc'] = 'asc'


class ProductRepository(typing.Protocol):
    def find_by_id(self, product_id: str) -> Product | None: ...
    def save(self, product: Product) -> None: ...

    # Paginated queries
    def find_all(self, page_request: PageRequest) -> Page[Product]: ...
    def find_by_category(
        self, category_id: str, page_request: PageRequest
    ) -> Page[Product]: ...

    def search(self, query: str, page_request: PageRequest) -> Page[Product]: ...
```

## Common Repository Methods

| Method              | Purpose           | Returns          |
| ------------------- | ------------------ | ----------------- |
| `find_by_id(id)`    | Get single entity | `Entity \| None` |
| `find_all()`        | Get all entities  | `list[Entity]`   |
| `save(entity)`      | Insert or update  | `None`           |
| `delete(id)`        | Remove entity     | `None`           |
| `exists_by_id(id)`  | Check existence   | `bool`           |
| `count()`           | Total count       | `int`            |

### Naming Conventions

```python
# Query methods start with "find"
def find_by_id(self, task_id: str) -> Task | None: ...
def find_by_user_id(self, user_id: str) -> list[Task]: ...
def find_by_status(self, status: TaskStatus) -> list[Task]: ...
def find_completed_before(self, date: datetime.datetime) -> list[Task]: ...

# Boolean checks use "exists" or "is"
def exists_by_id(self, task_id: str) -> bool: ...
def exists_by_email(self, email: Email) -> bool: ...

# Counts use "count"
def count(self) -> int: ...
def count_by_status(self, status: TaskStatus) -> int: ...
```

## Specification Pattern

For complex queries, define specifications in the domain:

```python
# src/domain/interfaces/task_repository.py
class TaskSpecification(typing.Protocol):
    def is_satisfied_by(self, task: Task) -> bool: ...
    def to_sql(self) -> tuple[str, list[typing.Any]] | None: ...  # Optional optimization


class TaskRepository(typing.Protocol):
    def find_by_id(self, task_id: str) -> Task | None: ...
    def find_all(self) -> list[Task]: ...
    def find_matching(self, spec: TaskSpecification) -> list[Task]: ...
    def save(self, task: Task) -> None: ...


# Usage in domain
class OverdueTaskSpecification:
    def __init__(self, now: datetime.datetime | None = None) -> None:
        self._now = now or datetime.datetime.now(datetime.UTC)

    def is_satisfied_by(self, task: Task) -> bool:
        return task.due_date < self._now and not task.is_completed

    def to_sql(self) -> tuple[str, list[typing.Any]]:
        return 'due_date < ? AND completed = 0', [self._now.isoformat()]
```

## Implementation Guidelines

### Infrastructure Implementation

```python
# src/infrastructure/repositories/sqlite_task_repository.py
import sqlite3

from src.domain.interfaces.task_repository import TaskRepository
from src.domain.entities.task import Task
from src.domain.value_objects.task_status import TaskStatus


@dataclasses.dataclass
class TaskRow:
    id: str
    user_id: str
    title: str
    completed: int  # SQLite boolean
    created_at: str


class SqliteTaskRepository(TaskRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def find_by_id(self, task_id: str) -> Task | None:
        row = self._conn.execute(
            'SELECT * FROM tasks WHERE id = ?', (task_id,)
        ).fetchone()

        return self._to_domain(row) if row is not None else None

    def find_all(self) -> list[Task]:
        rows = self._conn.execute(
            'SELECT * FROM tasks ORDER BY created_at DESC'
        ).fetchall()

        return [self._to_domain(row) for row in rows]

    def save(self, task: Task) -> None:
        self._conn.execute(
            """
            INSERT INTO tasks (id, user_id, title, completed, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              title = excluded.title,
              completed = excluded.completed
            """,
            (
                task.id,
                task.user_id,
                task.title,
                1 if task.is_completed else 0,
                task.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def delete(self, task_id: str) -> None:
        self._conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self._conn.commit()

    # Map database row to domain entity
    def _to_domain(self, row: sqlite3.Row) -> Task:
        return Task.reconstitute(
            id=row['id'],
            user_id=row['user_id'],
            title=row['title'],
            completed=row['completed'] == 1,
            created_at=datetime.datetime.fromisoformat(row['created_at']),
        )
```

### Unit of Work (Optional)

For transactional consistency across multiple repositories:

```python
# src/domain/interfaces/unit_of_work.py
class UnitOfWork(typing.Protocol):
    tasks: TaskRepository
    users: UserRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


# Usage in application layer
def execute(self, request: CreateOrderRequest) -> None:
    uow = self._unit_of_work_factory.create()
    try:
        user = uow.users.find_by_id(request.user_id)
        order = Order.create(...)
        uow.orders.save(order)
        uow.commit()
    except Exception:
        uow.rollback()
        raise
```

### Testing with Repository Interface

```python
# In-memory implementation for unit tests
class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def find_by_id(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def find_all(self) -> list[Task]:
        return list(self._tasks.values())

    def save(self, task: Task) -> None:
        self._tasks[task.id] = task

    def delete(self, task_id: str) -> None:
        del self._tasks[task_id]

    # Test helper
    def clear(self) -> None:
        self._tasks.clear()


# Use case test
class TestCreateTask:
    def setup_method(self) -> None:
        self.repository = InMemoryTaskRepository()
        self.use_case = CreateTask(self.repository)

    def test_creates_and_persists_task(self) -> None:
        result = self.use_case.execute(user_id='u1', title='Test')

        saved = self.repository.find_by_id(result.id)
        assert saved is not None
        assert saved.title == 'Test'
```
