# Violation Patterns Reference

## Table of Contents

1. [Domain Layer Violations](#domain-layer-violations)
2. [Application Layer Violations](#application-layer-violations)
3. [Interface Misplacement](#interface-misplacement)
4. [Common Framework Violations](#common-framework-violations)
5. [Database Schema Pollution](#database-schema-pollution)

---

## Domain Layer Violations

Domain code must be pure—no external dependencies.

### Infrastructure Import

**Bad:**

```python
# src/domain/entities/user.py
import sqlite3  # ❌
import requests  # ❌
```

**Fix:** Remove all infrastructure imports. Domain entities should only import other domain types.

### Direct Database Access

**Bad:**

```python
# src/domain/services/user_service.py
class UserService:
    async def find_user(self, db: sqlite3.Connection, user_id: str):  # ❌
        cursor = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()
```

**Fix:** Define a repository interface in domain, inject the implementation:

```python
# src/domain/interfaces/user_repository.py
from typing import Protocol


class UserRepository(Protocol):
    def find_by_id(self, user_id: str) -> "User | None": ...


# src/domain/services/user_service.py
class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def find_user(self, user_id: str) -> "User | None":
        return self.user_repo.find_by_id(user_id)
```

### HTTP/Request Objects in Domain

**Bad:**

```python
# src/domain/entities/task.py
from framework import Request  # ❌


class Task:
    @staticmethod
    def from_request(req: Request) -> "Task": ...  # ❌
```

**Fix:** Use plain DTOs. Parse requests in the presentation layer.

### Non-Essential I/O in Domain Logic

**Bad:**

```python
# src/domain/entities/order.py
class Order:
    def calculate_total(self) -> float:
        # ❌ - fetches exchange rates over the network
        rate = requests.get("https://api.exchange.com/rate").json()["rate"]
        return self.amount * rate
```

**Fix:** Pass rates as parameters or use domain services with injected dependencies.

---

## Application Layer Violations

Application layer orchestrates domain objects but must not know infrastructure details.

### Concrete Infrastructure Instantiation

**Bad:**

```python
# src/application/use_cases/create_user.py
from infrastructure.repositories.sql_user_repository import SqlUserRepository  # ❌


class CreateUser:
    def execute(self, data: "CreateUserRequest") -> None:
        repo = SqlUserRepository(db)  # ❌
        ...
```

**Fix:** Accept the interface via constructor:

```python
from domain.interfaces.user_repository import UserRepository


class CreateUser:
    def __init__(self, user_repo: UserRepository) -> None:  # ✓
        self.user_repo = user_repo

    def execute(self, data: "CreateUserRequest") -> None:
        # use self.user_repo
        ...
```

### Framework Types in Use Case Signatures

**Bad:**

```python
# src/application/use_cases/get_tasks.py
from framework import Request, Response  # ❌


class GetTasks:
    def execute(self, request: Request) -> Response:  # ❌
        ...
```

**Fix:** Use plain DTOs:

```python
class GetTasks:
    def execute(self, query: "GetTasksQuery") -> list["TaskResponse"]:  # ✓
        ...
```

### Direct External API Calls

**Bad:**

```python
# src/application/use_cases/send_notification.py
class SendNotification:
    def execute(self, user_id: str) -> None:
        requests.post("https://api.sendgrid.com/send", json={...})  # ❌
```

**Fix:** Define a port interface, inject an adapter:

```python
# src/domain/interfaces/notification_service.py
from typing import Protocol


class NotificationService(Protocol):
    def send(self, to: str, message: str) -> None: ...


# src/application/use_cases/send_notification.py
class SendNotification:
    def __init__(self, notifier: NotificationService) -> None:
        self.notifier = notifier

    def execute(self, user_id: str) -> None:
        self.notifier.send(user_id, "Hello")
```

---

## Interface Misplacement

Repository interfaces are ports—they belong in the domain layer.

### Interface in Infrastructure

**Bad:**

```
src/infrastructure/repositories/
├── user_repository.py     # Interface defined here ❌
└── sql_user_repository.py # Implementation
```

**Fix:**

```
src/domain/interfaces/
└── user_repository.py     # Interface here ✓

src/infrastructure/repositories/
└── sql_user_repository.py # Implementation imports interface
```

### Interface Importing Implementation Types

**Bad:**

```python
# src/domain/interfaces/cache_service.py
import redis  # ❌


class CacheService(Protocol):
    def get(self, key: str, client: redis.Redis) -> str | None: ...  # ❌
```

**Fix:** Keep the interface pure:

```python
class CacheService(Protocol):
    def get(self, key: str) -> str | None: ...  # ✓
```

---

## Common Framework Violations

### Web Framework Types

Violation indicators:

- `Request`/`Response`/`Context` types from a web framework in domain/application
- Middleware references in use cases
- Route handlers in application layer

### Database Drivers/ORMs

Violation indicators:

- ORM decorators or base classes on domain entities (e.g. SQLAlchemy `Base`,
  Django `models.Model`)
- Database connection/cursor types in domain interfaces
- Raw SQL client types (`sqlite3.Connection`, driver-specific connection
  objects) imported into domain code

### Validation Libraries

**Acceptable:** Using a validation library (e.g. `pydantic`) in application-layer DTOs
**Violation:** Validators/decorators directly on domain entities

```python
# Bad - domain entity
from pydantic import BaseModel  # ❌ in domain


class User(BaseModel):  # ❌ domain entity coupled to a validation framework
    email: str


# Good - application DTO
from pydantic import BaseModel


class CreateUserSchema(BaseModel):  # ✓ in application/dto
    email: str
```

---

## Database Schema Pollution

Domain entities must not have database-specific knowledge. Mapping between domain models and database rows belongs exclusively in the infrastructure layer (repository implementations).

### Domain Entity with Database Methods

**Bad:**

```python
# src/domain/entities/task.py
import dataclasses


@dataclasses.dataclass
class Task:
    id: str
    user_id: str
    completed: bool

    # ❌ Domain entity knows about database row shape
    def to_row(self) -> dict[str, object]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "completed": 1 if self.completed else 0,  # ❌ DB encoding in domain
        }

    # ❌ Domain entity knows how to reconstitute from a database row
    @classmethod
    def from_row(cls, row: dict[str, object]) -> "Task":
        return cls(row["id"], row["user_id"], row["completed"] == 1)
```

**Why this is wrong:**

1. **Domain knows database schema** - Entity is coupled to database table structure
2. **DB-specific encoding leaks in** - Boolean-to-integer conversion is an infrastructure concern
3. **Violates Single Responsibility** - Entity has both business logic and persistence logic

**Fix:** All mapping happens in the repository implementation:

```python
# src/domain/entities/task.py
import dataclasses
import uuid


@dataclasses.dataclass(frozen=True)
class Task:
    id: str
    user_id: str
    completed: bool

    # ✓ Pure factory method for creating new tasks
    @classmethod
    def create(cls, user_id: str) -> "Task":
        return cls(id=str(uuid.uuid4()), user_id=user_id, completed=False)

    # ✓ Reconstitution from trusted data (used by the repository)
    @classmethod
    def reconstitute(cls, id: str, user_id: str, completed: bool) -> "Task":
        return cls(id=id, user_id=user_id, completed=completed)

    # ✓ Business logic method
    def complete(self) -> "Task":
        if self.completed:
            raise DomainError("Task already completed")
        return dataclasses.replace(self, completed=True)


# src/infrastructure/repositories/sql_task_repository.py
from domain.entities.task import Task
from domain.interfaces.task_repository import TaskRepository


class SqlTaskRepository(TaskRepository):
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def save(self, task: Task) -> None:
        # ✓ Repository handles all mapping (row shape is private to this file)
        self.db.execute(
            "INSERT INTO tasks (id, user_id, completed) VALUES (?, ?, ?)",
            (task.id, task.user_id, 1 if task.completed else 0),  # ✓ encoding here
        )

    def find_by_id(self, task_id: str) -> Task | None:
        row = self.db.execute(
            "SELECT id, user_id, completed FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

        if row is None:
            return None

        # ✓ Repository handles reconstitution
        return Task.reconstitute(
            id=row["id"], user_id=row["user_id"], completed=row["completed"] == 1
        )
```

### Exposed Row Types

**Bad:**

```python
# src/domain/entities/user.py
class UserRow(TypedDict):  # ❌ Row type exported from domain
    id: str
    email: str
    created_at: str


class User:
    def to_row(self) -> UserRow:  # ❌
        ...
```

**Fix:** Row types are private to the repository:

```python
# src/domain/entities/user.py
class User:
    ...  # ✓ No row types, no to_row/from_row methods


# src/infrastructure/repositories/sql_user_repository.py
class _UserRow(TypedDict):  # ✓ Private to this module
    id: str
    email: str
    created_at: str


class SqlUserRepository:
    def _to_row(self, user: User) -> "_UserRow":  # ✓ Private mapping detail
        return {"id": str(user.id), "email": str(user.email), "created_at": user.created_at}

    def _to_domain(self, row: "_UserRow") -> User:  # ✓ Private mapping detail
        return User.reconstitute(
            id=UserId.from_string(row["id"]),
            email=Email.create(row["email"]),
            created_at=row["created_at"],
        )
```

### Detection Checklist

When reviewing code for database schema pollution:

- [ ] Domain entities have `to_row()` or `from_row()` methods
- [ ] Domain entities import database-specific types (`sqlite3.Connection`,
      an ORM base class, a driver's connection type)
- [ ] Domain has DB-specific encoding logic (boolean to int, enum to string, etc.)
- [ ] Row types (`*Row` / `TypedDict`s named after a table) defined in domain layer
- [ ] Repository interface exposes row types instead of domain entities

All of the above are violations. Mapping logic belongs exclusively in repository implementations.
