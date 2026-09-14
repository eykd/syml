# Data Security: Injection & Validation

## Table of Contents

- [SQL Injection Prevention](#sql-injection-prevention)
- [Input Validation](#input-validation)
- [Mass Assignment Protection](#mass-assignment-protection)
- [Secrets Management](#secrets-management)

## SQL Injection Prevention

### Parameterized Queries (Required)

```python
# ✅ CORRECT - Parameter binding
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
user = cursor.fetchone()

# ✅ CORRECT - Multiple parameters
cursor.execute(
    "SELECT * FROM tasks WHERE user_id = ? AND status = ?", (user_id, status)
)
tasks = cursor.fetchall()

# ❌ CRITICAL - String interpolation
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# ❌ CRITICAL - f-string / .format() with user input
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### Dynamic Query Building

```python
# Safe: Dynamic conditions with parameters
def build_query(filters: TaskFilters) -> tuple[str, list[object]]:
    conditions = ["user_id = ?"]
    params: list[object] = [filters.user_id]

    if filters.status:
        conditions.append("status = ?")
        params.append(filters.status)

    if filters.created_after:
        conditions.append("created_at > ?")
        params.append(filters.created_after.isoformat())

    sql = f"SELECT * FROM tasks WHERE {' AND '.join(conditions)} LIMIT ?"
    params.append(filters.limit or 50)
    return sql, params
```

### Safe Dynamic Column Names

```python
# Allowlist pattern for column names
ALLOWED_COLUMNS = {"created_at", "updated_at", "title", "status"}
ALLOWED_DIRECTIONS = {"ASC", "DESC"}


def build_order_clause(column: str, direction: str) -> str:
    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column: {column}")
    if direction.upper() not in ALLOWED_DIRECTIONS:
        raise ValueError(f"Invalid direction: {direction}")
    # Safe to interpolate after validation
    return f"ORDER BY {column} {direction.upper()}"
```

### Flag These as Critical

- Any string interpolation in SQL
- Template literals with user input in queries
- Dynamic table/column names without allowlist
- Raw SQL execution without parameterization

## Input Validation

### Validation Framework

```python
import dataclasses
import re


@dataclasses.dataclass(frozen=True)
class ValidationError:
    field: str
    message: str
    code: str


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    success: bool
    value: str | None = None
    errors: list[ValidationError] = dataclasses.field(default_factory=list)


class StringValidator:
    def __init__(
        self,
        field: str,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: re.Pattern[str] | None = None,
        required: bool = False,
    ) -> None:
        self.field = field
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.required = required

    def validate(self, value: object) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(
                success=False,
                errors=[ValidationError(self.field, "Must be a string", "INVALID_TYPE")],
            )

        trimmed = value.strip()
        errors: list[ValidationError] = []

        if self.required and not trimmed:
            errors.append(ValidationError(self.field, "Required", "REQUIRED"))
        if self.min_length and len(trimmed) < self.min_length:
            errors.append(
                ValidationError(self.field, f"Min {self.min_length} chars", "TOO_SHORT")
            )
        if self.max_length and len(trimmed) > self.max_length:
            errors.append(
                ValidationError(self.field, f"Max {self.max_length} chars", "TOO_LONG")
            )
        if self.pattern and not self.pattern.match(trimmed):
            errors.append(ValidationError(self.field, "Invalid format", "INVALID_FORMAT"))

        if errors:
            return ValidationResult(success=False, errors=errors)
        return ValidationResult(success=True, value=trimmed)
```

### Allowlist Validation

```python
import logging

logger = logging.getLogger(__name__)


# For fixed-set inputs (select boxes, radio buttons)
class AllowlistValidator:
    def __init__(self, field: str, allowed: frozenset[str]) -> None:
        self.field = field
        self.allowed = allowed

    def validate(self, value: object) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(
                success=False,
                errors=[ValidationError(self.field, "Must be a string", "INVALID_TYPE")],
            )

        if value not in self.allowed:
            # Log as security event - shouldn't happen with a valid client
            logger.warning("Allowlist violation field=%s value=%r", self.field, value)
            return ValidationResult(
                success=False,
                errors=[ValidationError(self.field, "Invalid selection", "NOT_ALLOWED")],
            )

        return ValidationResult(success=True, value=value)


# Usage
STATUSES = frozenset({"pending", "active", "completed"})
status_validator = AllowlistValidator("status", STATUSES)
```

### Email Validation

```python
class EmailValidator(StringValidator):
    PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def __init__(self, field: str) -> None:
        super().__init__(field, max_length=254, pattern=self.PATTERN)

    def validate(self, value: object) -> ValidationResult:
        result = super().validate(value)
        if not result.success or result.value is None:
            return result

        # Normalize for storage (prevent duplicate accounts)
        return ValidationResult(success=True, value=result.value.lower())
```

### Validation in Handlers

```python
def handle_create_user(request: Request) -> Response:
    body = request.json()

    validation = create_user_validator.validate(body)

    if not validation.success:
        return Response(
            render_validation_errors(validation.errors),
            status=422,
            content_type="text/html",
        )

    # Proceed with validated, typed data
    user = create_user(validation.value)
    return Response(render_success(user))
```

### Flag These as High

- Missing server-side validation
- Client-side only validation
- Type coercion without validation
- Missing length limits on strings

## Mass Assignment Protection

### Explicit Field Selection

```python
# ❌ WRONG - Updates any field client sends
def update_user(user_id: str, data: dict[str, object]) -> None:
    columns = ", ".join(f"{k} = ?" for k in data)
    cursor.execute(f"UPDATE users SET {columns} WHERE id = ?", (*data.values(), user_id))


# ✅ CORRECT - Explicit allowed fields
@dataclasses.dataclass(frozen=True)
class UpdateUserRequest:
    name: str | None = None
    email: str | None = None
    # Note: no 'role' or 'is_admin' fields


def update_user_safely(user_id: str, data: UpdateUserRequest) -> None:
    updates: list[str] = []
    params: list[object] = []

    if data.name is not None:
        updates.append("name = ?")
        params.append(data.name)
    if data.email is not None:
        updates.append("email = ?")
        params.append(data.email)

    if not updates:
        return

    params.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
```

### DTO Pattern

```python
# Define exactly what's accepted
@dataclasses.dataclass(frozen=True)
class CreateTaskDto:
    title: str
    description: str
    status: str  # 'pending' | 'active'
    # Explicitly omit: user_id, created_at, id (set server-side)


def create_task(dto: CreateTaskDto, user_id: str) -> Task:
    return Task(
        id=generate_id(),  # Server-controlled
        user_id=user_id,  # From session
        created_at=datetime.now(timezone.utc),  # Server-controlled
        title=dto.title,
        description=dto.description,
        status=dto.status,
    )
```

### Flag These as High

- Spreading request body into entities
- Dynamic updates from user input
- Missing field allowlists

## Secrets Management

### Environment Variables

```python
import os

# ✅ CORRECT - Access via environment variable
api_key = os.environ["API_SECRET"]

# ❌ CRITICAL - Hardcoded secrets
API_KEY = "sk-abc123..."
DB_PASSWORD = "password123"
```

### CI / Publishing Secrets

```bash
# Set secrets via the CI provider's secret store (e.g. GitHub Actions),
# never committed to pyproject.toml or any tracked file.
gh secret set PYPI_API_TOKEN
```

### Flag These as Critical

- Secrets in source code
- Secrets in config files committed to git
- API keys in client-side code
- Secrets in error messages or logs

### Secrets Checklist

- [ ] No hardcoded secrets
- [ ] Secrets in environment variables
- [ ] Secrets not logged
- [ ] Secrets not in error responses
- [ ] Different secrets per environment
- [ ] Secret rotation capability
