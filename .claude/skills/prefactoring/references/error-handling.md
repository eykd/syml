# Error Handling Strategies

**Purpose**: Apply prefactoring principles for robust error handling, meaningful messages, and resilient systems.

## When to Use

- Designing error handling strategies
- Implementing catch blocks
- Creating user-facing error messages
- Building resilient external integrations

## Core Principles

### Never Be Silent

Every error must be reported. Never swallow exceptions without handling.

```python
# Bad: Silent failure
try:
    await send_notification(user)
except Exception:
    pass  # Error ignored - user never knows

# Good: Always report
try:
    await send_notification(user)
except Exception as error:
    self.logger.error('Notification failed', extra={'user_id': user.id, 'error': error})
    raise NotificationFailedError(user.id) from error
```

### Report Meaningful User Messages

Error messages describe what users can do, not technical details.

```python
# Bad: Technical error exposed
raise ValueError('UNIQUE constraint failed: users.email')

# Good: User-actionable message
raise UserFacingError(
    'An account with this email already exists. Please sign in or use a different email.',
    code='EMAIL_EXISTS',
    technical_details=original_error,
)
```

### Consider Failure an Expectation

Design for failure with retries, fallbacks, and graceful degradation.

```python
class ResilientNotificationService:
    async def notify(self, user: User, message: Message) -> Result[None]:
        # Retry with backoff
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = await self._try_notify(user, message)
            if result.success:
                return result
            await self._backoff(attempt)

        # Fallback
        await self._queue_for_later_delivery(user, message)
        return Result.ok(None)
```

## Result Type Pattern

Use a Result type to make errors explicit in the type system.

```python
@dataclass(frozen=True)
class Result(Generic[T]):
    success: bool
    value: T | None = None
    error: Exception | None = None

    @classmethod
    def ok(cls, value: T) -> 'Result[T]':
        return cls(success=True, value=value)

    @classmethod
    def fail(cls, error: Exception) -> 'Result[T]':
        return cls(success=False, error=error)


def parse_email(input: str) -> Result[Email]:
    if '@' not in input:
        return Result.fail(ValidationError('Invalid email'))
    return Result.ok(Email(input))


# Usage forces error handling
result = parse_email(input)
if not result.success:
    return Response.json({'error': str(result.error)}, status=400)
email = result.value  # Type-safe access
```

## Decision Matrix

| Situation           | Apply                  | Example                        |
| ------------------- | ---------------------- | ------------------------------ |
| Catch block         | Never Be Silent        | Log and re-throw or handle     |
| User-facing error   | Meaningful Messages    | Explain what user can do       |
| External dependency | Failure as Expectation | Add retry/fallback             |
| Function can fail   | Result Type            | Return Result instead of throw |

## Related References

- [contracts.md](./contracts.md): Validation and interface contracts
- [value-objects.md](./value-objects.md): Domain types with validation
