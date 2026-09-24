# Validation Architecture

## Three-Layer Validation Strategy

Validation in a Clean Architecture application happens at **three distinct layers**, each with different responsibilities:

```
┌──────────────────────────────────────────────────┐
│ Layer 1: Presentation (Input Validation)        │
│ - Type checking (string, number, boolean)       │
│ - Format validation (email format, UUID format)  │
│ - Allowlist validation (enum values)            │
│ - Length limits, character restrictions          │
│ - Returns: 422 Unprocessable Entity              │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ Layer 2: Domain (Business Rule Validation)      │
│ - Business logic rules                           │
│ - Value object constraints                       │
│ - Entity invariants                              │
│ - Throws: ValidationError, DomainError           │
└──────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│ Layer 3: Infrastructure (Constraint Validation) │
│ - Uniqueness constraints (UNIQUE indexes)        │
│ - Foreign key constraints                        │
│ - Database-level validation                      │
│ - Throws: ConflictError (from UNIQUE violation)  │
└──────────────────────────────────────────────────┘
```

## Layer 1: Presentation Validation

**Purpose**: Validate request format and type before passing to application layer.

**Location**: HTTP handlers, before calling use cases.

**Tools**: String validators, allowlist validators, format checkers.

**Returns**: 422 status code with field-level errors.

### Implementation

```python
# String validator
class StringValidator:
    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: re.Pattern[str] | None = None,
    ) -> None:
        self._min_length = min_length
        self._max_length = max_length
        self._pattern = pattern

    def validate(self, value: object) -> Result[str, ValidationError]:
        if not isinstance(value, str):
            return err(ValidationError('Must be a string'))

        if self._min_length and len(value) < self._min_length:
            return err(ValidationError(f'Must be at least {self._min_length} characters'))

        if self._max_length and len(value) > self._max_length:
            return err(ValidationError(f'Must be at most {self._max_length} characters'))

        if self._pattern and not self._pattern.match(value):
            return err(ValidationError('Invalid format'))

        return ok(value)


# Allowlist validator
class AllowlistValidator(typing.Generic[T]):
    def __init__(self, allowed_values: typing.Sequence[T]) -> None:
        self._allowed_values = allowed_values

    def validate(self, value: object) -> Result[T, ValidationError]:
        if not isinstance(value, str):
            return err(ValidationError('Must be a string'))

        if value not in self._allowed_values:
            joined = ', '.join(self._allowed_values)
            return err(ValidationError(f'Must be one of: {joined}'))

        return ok(typing.cast(T, value))
```

### Handler Usage

```python
def handle_create_task(request: Request) -> Response:
    body = request.json()

    # Layer 1: Presentation validation
    title_validator = StringValidator(3, 200)
    priority_validator = AllowlistValidator(['low', 'medium', 'high'])

    title_result = title_validator.validate(body['title'])
    if not title_result.success:
        return json_response(422, {
            'error': 'Invalid request data',
            'fields': {'title': [title_result.error.message]},
        })

    priority_result = priority_validator.validate(body['priority'])
    if not priority_result.success:
        return json_response(422, {
            'error': 'Invalid request data',
            'fields': {'priority': [priority_result.error.message]},
        })

    # Pass validated data to use case
    dto = CreateTaskDto(
        title=title_result.value,
        priority=priority_result.value,
        user_id=body['userId'],
    )

    result = create_task_use_case.execute(dto)

    if not result.success:
        return error_response(result.error)

    return json_response(201, to_task_response(result.value))
```

### Validation Schema Pattern

For complex requests, use a validation schema:

```python
class SchemaValidator(typing.Generic[T]):
    def __init__(self, schema: dict[str, Validator[typing.Any]]) -> None:
        self._schema = schema

    def validate(self, data: object) -> Result[T, ValidationError]:
        if not isinstance(data, dict):
            return err(ValidationError('Must be an object'))

        validated: dict[str, typing.Any] = {}
        errors: dict[str, list[str]] = {}

        for key, validator in self._schema.items():
            value = data.get(key)
            result = validator.validate(value)

            if not result.success:
                errors[key] = [result.error.message]
            else:
                validated[key] = result.value

        if len(errors) > 0:
            return err(ValidationError('Validation failed', errors))

        return ok(typing.cast(T, validated))


# Usage
create_task_schema = SchemaValidator[CreateTaskDto]({
    'title': StringValidator(3, 200),
    'priority': AllowlistValidator(['low', 'medium', 'high']),
    'userId': StringValidator(36, 36, UUID_PATTERN),
})

result = create_task_schema.validate(body)
if not result.success:
    return json_response(422, {
        'error': 'Invalid request data',
        'fields': result.error.fields,
    })
```

## Layer 2: Domain Validation

**Purpose**: Enforce business rules and entity invariants.

**Location**: Entity constructors, value object constructors, domain methods.

**Tools**: Raise ValidationError, raise DomainError.

**Returns**: Use case catches and returns Result<T, ValidationError>.

### Value Object Validation

```python
@dataclasses.dataclass(frozen=True)
class Email:
    value: str

    @classmethod
    def create(cls, value: str) -> 'Email':
        # Business rule: email must be normalized lowercase
        normalized = value.lower().strip()

        # Business rule: email must match format
        if not cls._is_valid_format(normalized):
            raise ValidationError('Invalid email format')

        # Business rule: no disposable email domains
        if cls._is_disposable(normalized):
            raise ValidationError('Disposable email addresses are not allowed')

        return cls(normalized)

    @staticmethod
    def _is_valid_format(email: str) -> bool:
        return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email))

    @staticmethod
    def _is_disposable(email: str) -> bool:
        domain = email.split('@')[1]
        return domain in ('tempmail.com', '10minutemail.com')

    def __str__(self) -> str:
        return self.value
```

### Entity Validation

```python
class Task:
    def __init__(
        self, id: TaskId, title: str, user_id: UserId, completed: bool
    ) -> None:
        self._id = id
        self._title = title
        self._user_id = user_id
        self._completed = completed

    @classmethod
    def create(cls, *, title: str, user_id: UserId) -> 'Task':
        # Business rule: title must not be empty after trim
        trimmed = title.strip()
        if len(trimmed) == 0:
            raise ValidationError('Task title cannot be empty')

        # Business rule: title must not contain profanity
        if cls._contains_profanity(trimmed):
            raise ValidationError('Task title contains inappropriate content')

        return cls(TaskId.generate(), trimmed, user_id, False)

    def complete(self) -> None:
        # Business rule: cannot complete already completed task
        if self._completed:
            raise DomainError('Task is already completed')

        self._completed = True

    @staticmethod
    def _contains_profanity(text: str) -> bool:
        # Business logic for profanity detection
        return False
```

### Use Case Error Handling

```python
class CreateTaskUseCase:
    def execute(self, dto: CreateTaskDto) -> Result[Task, ValidationError | ConflictError]:
        # Layer 2: Domain validation (catch exceptions)
        try:
            user_id = UserId.from_string(dto.user_id)
            task = Task.create(title=dto.title, user_id=user_id)

            # Layer 3: Infrastructure (catch exceptions)
            try:
                self._repository.save(task)
                return ok(task)
            except ConflictError as error:
                return err(error)

        except ValidationError as error:
            return err(error)  # Domain validation error
        except DomainError as error:
            return err(ValidationError(str(error)))
```

## Layer 3: Infrastructure Validation

**Purpose**: Enforce database constraints (uniqueness, foreign keys).

**Location**: Repository implementations.

**Tools**: Catch UNIQUE constraint violations, raise ConflictError.

**Returns**: Use case catches and returns Result<T, ConflictError>.

### Repository Implementation

```python
class SqliteTaskRepository(TaskRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, task: Task) -> None:
        query = """
            INSERT INTO tasks (id, user_id, title, completed)
            VALUES (?, ?, ?, ?)
        """

        try:
            self._conn.execute(
                query,
                (
                    task.get_id().value,
                    task.get_user_id().value,
                    task.get_title(),
                    1 if task.is_completed() else 0,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as error:
            # Layer 3: Uniqueness constraint violation
            if 'UNIQUE constraint failed' in str(error):
                raise ConflictError('Task already exists') from error

            # Layer 3: Foreign key constraint violation
            if 'FOREIGN KEY constraint failed' in str(error):
                raise ValidationError('User does not exist') from error

            # Infrastructure error (connection lost, etc.)
            raise DatabaseError('Failed to save task', query, error) from error

    def find_by_user_and_title(self, user_id: UserId, title: str) -> Task | None:
        query = """
            SELECT id, user_id, title, completed
            FROM tasks
            WHERE user_id = ? AND title = ?
        """

        try:
            row = self._conn.execute(query, (user_id.value, title)).fetchone()

            if row is None:
                return None

            return self._to_domain(row)
        except sqlite3.Error as error:
            raise DatabaseError('Failed to find task', query, error) from error

    def _to_domain(self, row: sqlite3.Row) -> Task:
        return Task.reconstitute(
            id=TaskId.from_string(row['id']),
            user_id=UserId.from_string(row['user_id']),
            title=row['title'],
            completed=row['completed'] == 1,
        )
```

### Database Schema with Constraints

```sql
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),

  -- Layer 3: Uniqueness constraint
  UNIQUE(user_id, title),

  -- Layer 3: Foreign key constraint
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Layer 3: Index for lookups
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
```

## Validation Flow Summary

### Example: Create Task Request

```python
# Request body
{
    'title': '  Buy groceries  ',
    'priority': 'high',
    'userId': '123e4567-e89b-12d3-a456-426614174000',
}

# Layer 1: Presentation (HTTP handler)
# title is string, 3-200 chars
# priority is 'low' | 'medium' | 'high'
# userId is valid UUID format
# -> Pass to use case

# Layer 2: Domain (Entity)
# Trim title: "Buy groceries"
# Title not empty after trim
# Title contains no profanity
# -> Create entity

# Layer 3: Infrastructure (Repository)
# Check UNIQUE(user_id, title)
# User already has task "Buy groceries"
# -> Raise ConflictError

# Use case catches ConflictError
# -> Return err(ConflictError)

# Handler maps to HTTP response
# -> 409 Conflict
{
    'error': 'Resource already exists',
    'code': 'CONFLICT',
}
```

## Anti-Patterns

### ❌ Validation in Wrong Layer

```python
# WRONG - Business logic in presentation layer
def handle_create_task(request: Request) -> Response:
    body = request.json()

    # Business rule (profanity check) in presentation layer
    if contains_profanity(body['title']):
        return json_response(422, {'error': 'Title contains profanity'})

    # This belongs in domain layer (Task.create)


# WRONG - Format validation in domain layer
@dataclasses.dataclass(frozen=True)
class Email:
    value: str

    @classmethod
    def create(cls, value: object) -> 'Email':
        # Type checking belongs in presentation layer
        if not isinstance(value, str):
            raise ValidationError('Email must be a string')

        # Business rules belong here
        if not cls._is_valid_format(value):
            raise ValidationError('Invalid email format')

        return cls(value)
```

### ❌ Duplicate Validation

```python
# WRONG - Duplicate validation in multiple layers
def handle_create_task(request: Request) -> Response:
    body = request.json()

    # Checking title length here
    if not body.get('title') or len(body['title']) < 3:
        return json_response(422, {'error': 'Title too short'})

    dto = {'title': body['title'], 'userId': body['userId']}
    result = create_task_use_case.execute(dto)
    # ...


class Task:
    @classmethod
    def create(cls, *, title: str) -> 'Task':
        # And also checking title length here
        if len(title) < 3:
            raise ValidationError('Title too short')
        # ...
```

### ✅ Correct: Single Responsibility

```python
# CORRECT - Format validation in presentation
def handle_create_task(request: Request) -> Response:
    body = request.json()

    # Format validation only
    title_validator = StringValidator(3, 200)
    title_result = title_validator.validate(body['title'])
    if not title_result.success:
        return json_response(422, {'error': 'Invalid format'})

    dto = {'title': title_result.value, 'userId': body['userId']}
    result = create_task_use_case.execute(dto)
    # ...


# CORRECT - Business rules in domain
class Task:
    @classmethod
    def create(cls, *, title: str) -> 'Task':
        # Business rules only
        trimmed = title.strip()
        if len(trimmed) == 0:
            raise ValidationError('Title cannot be empty')
        if cls._contains_profanity(trimmed):
            raise ValidationError('Title contains profanity')
        return cls(TaskId.generate(), trimmed, False)
```

## Testing Each Layer

### Test Presentation Validation

```python
class TestStringValidator:
    def test_validates_string_length(self) -> None:
        validator = StringValidator(3, 10)

        assert validator.validate('ab').success is False
        assert validator.validate('abc').success is True
        assert validator.validate('1234567890').success is True
        assert validator.validate('12345678901').success is False


class TestHandleCreateTask:
    def test_returns_422_for_invalid_title_format(self) -> None:
        request = Request(
            method='POST',
            body=json.dumps({'title': 'ab', 'userId': 'user-1'}),
        )

        response = handle_create_task(request)

        assert response.status == 422
```

### Test Domain Validation

```python
class TestTaskCreate:
    def test_raises_validation_error_for_empty_title(self) -> None:
        with pytest.raises(ValidationError):
            Task.create(title='   ', user_id=UserId.generate())

    def test_raises_validation_error_for_profanity(self) -> None:
        with pytest.raises(ValidationError):
            Task.create(title='bad word here', user_id=UserId.generate())

    def test_creates_task_with_valid_title(self) -> None:
        task = Task.create(title='Valid title', user_id=UserId.generate())
        assert isinstance(task, Task)
```

### Test Infrastructure Validation

```python
class TestSqliteTaskRepository:
    def test_raises_conflict_error_for_duplicate_task(self) -> None:
        task = Task.create(title='Buy groceries', user_id=UserId.generate())

        self.repository.save(task)

        duplicate = Task.create(title='Buy groceries', user_id=task.get_user_id())

        with pytest.raises(ConflictError):
            self.repository.save(duplicate)

    def test_raises_validation_error_for_invalid_foreign_key(self) -> None:
        invalid_user_id = UserId.generate()
        task = Task.create(title='Test', user_id=invalid_user_id)

        with pytest.raises(ValidationError):
            self.repository.save(task)
```

## Best Practices

1. **Single Responsibility**: Each layer validates what it's responsible for
2. **No Duplication**: Don't validate the same thing in multiple layers
3. **Fail Fast**: Validate at the earliest appropriate layer
4. **Clear Errors**: Use specific error types (ValidationError, ConflictError)
5. **Type Safety**: Use type hints (mypy) to prevent invalid states
6. **Test Each Layer**: Unit test validators, domain logic, and constraints separately

## Related Skills

- **error-handling-patterns**: Result types, error hierarchy, error responses
- **security-audit**: Input validation, allowlist validation, metadata validation
- **ddd-domain-modeling**: Value objects, entities, domain errors
