# Authentication & Session Security

## Table of Contents

- [Password Hashing](#password-hashing)
- [Session Management](#session-management)
- [Brute Force Protection](#brute-force-protection)
- [Timing Attack Prevention](#timing-attack-prevention)

## Password Hashing

### Required: Argon2id

OWASP 2025 recommendation. Protects against GPU and side-channel attacks.

```python
import argon2

config = argon2.PasswordHasher(
    memory_cost=19456,  # 19 MiB minimum
    time_cost=2,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return config.hash(password)
```

### Flag These as Critical

- `md5()`, `sha1()`, `sha256()` without salt
- `bcrypt` (use Argon2id instead)
- Plain text passwords
- Reversible encryption for passwords

### Password Requirements

- Minimum 12 characters (NIST 800-63B)
- Maximum 128 characters
- Check against common password list
- No complexity requirements (per NIST)

## Session Management

### Secure Cookie Pattern

```python
cookie = (
    f"__Host-session={session_id}; "  # __Host- prefix required
    "HttpOnly; "  # No JavaScript access
    "Secure; "  # HTTPS only
    "SameSite=Lax; "  # CSRF protection
    "Path=/; "  # Required for __Host-
    f"Max-Age={SESSION_TTL}"
)
```

### Session ID Requirements

- 256+ bits cryptographic randomness
- Generated server-side only
- Regenerate on privilege changes (login, role change)

```python
import secrets


def generate_session_id() -> str:
    return secrets.token_hex(32)
```

### Session Storage

```python
# Store with a TTL for automatic expiration (illustrative; use whatever
# key-value store or session backend the application already has).
session_store.set(
    f"session:{session_id}",
    {"user_id": user_id, "csrf_token": csrf_token, "created_at": created_at},
    ttl_seconds=86400,  # 24 hours
)
```

### Flag These as High

- Session IDs in URLs
- Missing `HttpOnly` flag
- Missing `Secure` flag
- `SameSite=None` without justification
- Long session lifetimes without refresh

## Brute Force Protection

### Account Lockout

```python
import dataclasses
from datetime import datetime, timedelta, timezone


@dataclasses.dataclass(frozen=True)
class User:
    MAX_FAILED_ATTEMPTS = 5
    LOCK_DURATION = timedelta(minutes=15)

    failed_login_attempts: int = 0
    locked_until: datetime | None = None

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def record_failed_login(self) -> "User":
        attempts = self.failed_login_attempts + 1
        should_lock = attempts >= self.MAX_FAILED_ATTEMPTS
        locked_until = datetime.now(timezone.utc) + self.LOCK_DURATION if should_lock else None
        return dataclasses.replace(
            self, failed_login_attempts=attempts, locked_until=locked_until
        )
```

### Rate Limiting (Sliding Window)

```python
import dataclasses
from datetime import datetime


@dataclasses.dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: datetime


def check_rate_limit(key: str, limit: int, window_seconds: float) -> RateLimitResult:
    # Sliding window implementation...
    raise NotImplementedError


# Apply to auth endpoints
ip_limit = check_rate_limit(f"ip:{client_ip}", 10, 60)
account_limit = check_rate_limit(f"account:{email}", 5, 300)
```

### Flag These as High

- Auth endpoints without rate limiting
- No account lockout after failed attempts
- Missing IP-based rate limiting
- Lockout bypass via password reset

## Timing Attack Prevention

### Constant-Time Comparison

```python
import hmac


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# For bytes
def constant_time_equal_bytes(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)
```

### Use For

- Password verification
- CSRF token validation
- API key comparison
- Session ID comparison
- Any security-sensitive string comparison

### Flag These as High

- `==` for tokens/secrets (use `hmac.compare_digest` instead)
- Early return on mismatch
- Length-revealing comparisons before the full value is checked

## Account Enumeration Prevention

### Generic Error Messages

```python
# ❌ Wrong - reveals valid accounts
if not user:
    return error("User not found")
if not valid_password:
    return error("Invalid password")

# ✅ Correct - generic message
if not user or not valid_password:
    return error("Invalid email or password")
```

### Consistent Timing

```python
DUMMY_HASH = "$argon2id$v=19$m=19456,t=2,p=1$..."


def login(email: str, password: str) -> Response:
    user = find_user(email)

    # Always hash even if user not found (prevents timing leak)
    hash_to_verify = user.password_hash if user else DUMMY_HASH

    valid = verify_password(password, hash_to_verify)

    if not user or not valid:
        return error("Invalid email or password")
    ...
```
