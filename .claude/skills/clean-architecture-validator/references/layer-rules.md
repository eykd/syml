# Layer Rules Reference

## Table of Contents

1. [Layer Overview](#layer-overview)
2. [Dependency Matrix](#dependency-matrix)
3. [Layer Contents](#layer-contents)
4. [Directory Mapping](#directory-mapping)
5. [Refactoring Patterns](#refactoring-patterns)

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│   (Handlers, Controllers, Templates, CLI)                   │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                      │
│   (Repositories, External APIs, Caches, File System)        │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│   (Use Cases, DTOs, Application Services)                   │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│   (Entities, Value Objects, Domain Services, Interfaces)    │
└─────────────────────────────────────────────────────────────┘
                    Dependencies point DOWN ↓
```

---

## Dependency Matrix

| From \ To          | Domain | Application | Infrastructure | Presentation |
| ------------------ | ------ | ----------- | -------------- | ------------ |
| **Domain**         | ✓      | ❌          | ❌             | ❌           |
| **Application**    | ✓      | ✓           | ❌             | ❌           |
| **Infrastructure** | ✓      | ✓           | ✓              | ❌           |
| **Presentation**   | ✓      | ✓           | ✓              | ✓            |

**Key rule:** ✓ = allowed, ❌ = violation

---

## Layer Contents

### Domain Layer

**Purpose:** Core business logic and rules, independent of technical concerns.

**Contains:**

- Entities (aggregate roots with identity)
- Value Objects (immutable, identity-less)
- Domain Services (operations spanning entities)
- Repository Interfaces (ports for data access)
- Domain Events
- Domain Exceptions

**Allowed imports:**

- Other domain types only
- Language built-ins (Date, Map, Set, etc.)

**Forbidden:**

- Framework packages
- Database clients
- HTTP types
- File system APIs
- External service clients

### Application Layer

**Purpose:** Orchestrate domain objects to fulfill use cases.

**Contains:**

- Use Cases / Application Services
- DTOs (Data Transfer Objects)
- Input/Output boundaries
- Application Events
- Validation schemas (for DTOs)

**Allowed imports:**

- Domain types (entities, value objects, interfaces)
- Application types (DTOs, other use cases)

**Forbidden:**

- Infrastructure implementations
- Presentation types (Request, Response)
- Framework-specific decorators

### Infrastructure Layer

**Purpose:** Implement technical concerns and integrate with external systems.

**Contains:**

- Repository Implementations
- External API Clients
- Cache Implementations
- Message Queue Adapters
- File System Access
- Database Migrations

**Allowed imports:**

- Domain interfaces (to implement)
- Application types (to use DTOs)
- Framework packages
- Database clients
- External SDKs

### Presentation Layer

**Purpose:** Handle HTTP/CLI/UI and translate to application calls.

**Contains:**

- HTTP Handlers / Controllers
- Route Definitions
- Middleware
- HTML Templates
- CLI Commands
- Request/Response Mapping

**Allowed imports:**

- Application use cases
- Domain types (for response mapping)
- Infrastructure (for dependency injection setup)
- Framework packages

---

## Directory Mapping

### Standard Structure

```
src/
├── domain/
│   ├── entities/
│   ├── value-objects/
│   ├── services/
│   └── interfaces/        # Repository/port interfaces HERE
│
├── application/
│   ├── use-cases/
│   ├── dto/
│   └── services/
│
├── infrastructure/
│   ├── repositories/      # Implements domain/interfaces
│   ├── cache/
│   ├── external/
│   └── persistence/
│
└── presentation/
    ├── handlers/
    ├── middleware/
    ├── templates/
    └── routes/
```

### Alternative Names

Some projects use different names:

| Standard       | Alternatives                    |
| -------------- | ------------------------------- |
| domain         | core, model, business           |
| application    | use-cases, services, app        |
| infrastructure | adapters, data, external, infra |
| presentation   | web, api, http, ui, cli         |

---

## Refactoring Patterns

### Extract Interface to Domain

**Before:**

```
infrastructure/repositories/user_repository.py  # interface + impl
```

**After:**

```
domain/interfaces/user_repository.py             # interface only
infrastructure/repositories/sql_user_repository.py # implementation
```

### Remove Infrastructure from Domain

**Before:**

```python
# domain/entities/user.py
from infrastructure.database import db


class User:
    def save(self) -> None:
        db.insert("users", self)
```

**After:**

```python
# domain/entities/user.py
class User:
    ...  # Pure entity, no persistence


# domain/interfaces/user_repository.py
from typing import Protocol


class UserRepository(Protocol):
    def save(self, user: User) -> None: ...


# infrastructure/repositories/sql_user_repository.py
class SqlUserRepository(UserRepository):
    def save(self, user: User) -> None:
        self.db.insert("users", user)
```

### Remove Framework Types from Use Cases

**Before:**

```python
# application/use_cases/create_user.py
def execute(self, request: Request) -> Response: ...
```

**After:**

```python
# application/dto/create_user_request.py
import dataclasses


@dataclasses.dataclass(frozen=True)
class CreateUserRequest:
    email: str
    name: str


# application/use_cases/create_user.py
def execute(self, dto: CreateUserRequest) -> "UserResponse": ...


# presentation/handlers/user_handler.py
def handle_create(self, request: Request) -> Response:
    dto = self.parse_request(request)
    result = self.create_user.execute(dto)
    return self.to_response(result)
```

### Dependency Injection Setup

Wire dependencies in a composition root (entry point):

```python
# src/composition_root.py
def build_app(config: Config) -> App:
    # Create infrastructure implementations
    user_repo = SqlUserRepository(config.db)
    cache = FileCacheService(config.cache_dir)

    # Create use cases with injected dependencies
    create_user = CreateUser(user_repo)
    get_user = GetUser(user_repo, cache)

    # Create handlers with use cases
    handlers = UserHandlers(create_user, get_user)

    return App(handlers)
```
