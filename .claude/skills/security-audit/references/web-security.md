# Web Security: XSS, CSRF, CSP, Headers

## Table of Contents

- [XSS Prevention](#xss-prevention)
- [CSRF Protection](#csrf-protection)
- [Content Security Policy](#content-security-policy)
- [Security Headers](#security-headers)

## XSS Prevention

### Output Encoding (Primary Defense)

```python
import html


def encode(text: str) -> str:
    return html.escape(text, quote=True)


# Usage — always encode before interpolating into markup
rendered = f'<div class="user">{encode(user.name)}</div>'  # Explicit encoding
```

### Context-Specific Encoding

| Context        | Encoding Required                      |
| -------------- | -------------------------------------- |
| HTML body      | `&<>"'` → entities                     |
| HTML attribute | `&<>"'` → entities + quote attribute   |
| JavaScript     | JSON.stringify or escape special chars |
| URL            | encodeURIComponent                     |
| CSS            | Avoid user input; whitelist if needed  |

### Flag These as Critical

- String interpolation into HTML/markup without encoding
- Templating with autoescaping disabled for a block containing user data
- `eval()`/`exec()` with any externally-influenced input
- Building shell commands or SQL from unescaped user data (the same
  injection class as XSS, different sink)

## CSRF Protection

### Session-Tied CSRF Tokens

```python
# Generate token with session
def create_session(user_id: str) -> Session:
    csrf_token = generate_secure_token()  # 256 bits
    return Session(
        session_id=generate_session_id(),
        user_id=user_id,
        csrf_token=csrf_token,  # Stored in session, not separate
    )


# Validate in middleware
def validate_csrf(session: Session, token: str) -> bool:
    return session.validate_csrf_token(token)  # Constant-time compare
```

### Include Token in Requests

```html
<!-- Via a hidden field for forms -->
<form method="post">
  <input type="hidden" name="_csrf" value="${csrfToken}" />
</form>
<!-- Or via a custom header for XHR/fetch requests -->
```

### CSRF Middleware

```python
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def csrf_middleware(request: Request, session: Session | None) -> Response | None:
    if request.method.upper() in SAFE_METHODS:
        return None

    if session is None:
        return Response("Unauthorized", status=401)

    token = request.headers.get("X-CSRF-Token") or extract_from_form(request)

    if not token or not session.validate_csrf_token(token):
        return Response("CSRF validation failed", status=403)

    if not validate_origin(request):
        return Response("Invalid origin", status=403)

    return None  # Continue
```

### Origin Validation

```python
from urllib.parse import urlparse


def validate_origin(request: Request) -> bool:
    origin = request.headers.get("Origin")
    host = request.headers.get("Host")

    if not origin:
        referer = request.headers.get("Referer")
        if not referer:
            return True  # Allow but log
        try:
            return urlparse(referer).netloc == host
        except ValueError:
            return False

    try:
        return urlparse(origin).netloc == host
    except ValueError:
        return False
```

### Flag These as High

- State-changing endpoints without CSRF validation
- CSRF tokens not tied to sessions
- Missing Origin/Referer validation
- GET requests that modify state

## Content Security Policy

### Recommended CSP

```python
def build_csp(nonce: str | None = None) -> str:
    directives = {
        "default-src": ["'self'"],
        "script-src": ["'self'", f"'nonce-{nonce}'" if nonce else ""],
        "style-src": ["'self'"],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "object-src": ["'none'"],
    }

    return "; ".join(
        f"{key} {' '.join(v for v in values if v)}" for key, values in directives.items()
    )
```

### CSP Directive Reference

| Directive         | Purpose                                  |
| ----------------- | ---------------------------------------- |
| `default-src`     | Fallback for all fetches                 |
| `script-src`      | JavaScript sources                       |
| `style-src`       | CSS sources                              |
| `connect-src`     | XHR, fetch, WebSocket                    |
| `frame-ancestors` | Who can embed (replaces X-Frame-Options) |
| `form-action`     | Form submission targets                  |
| `base-uri`        | Allowed `<base>` URLs                    |

### Flag These as Medium

- Missing CSP header
- `unsafe-inline` for scripts
- `unsafe-eval` without justification
- Overly permissive `default-src`

## Security Headers

### Required Headers

```python
def add_security_headers(response: Response) -> Response:
    # HSTS - force HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Clickjacking protection
    response.headers["X-Frame-Options"] = "DENY"

    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions policy
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    return response
```

### Header Checklist

| Header                      | Value                                 | Purpose               |
| --------------------------- | ------------------------------------- | --------------------- |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` | Force HTTPS           |
| `X-Content-Type-Options`    | `nosniff`                             | Prevent MIME sniffing |
| `X-Frame-Options`           | `DENY`                                | Prevent clickjacking  |
| `Content-Security-Policy`   | See above                             | Resource restrictions |
| `Referrer-Policy`           | `strict-origin-when-cross-origin`     | Control referrer      |
| `Permissions-Policy`        | `camera=(), microphone=()`            | Disable features      |

### Cache Control for Authenticated Content

```python
# Prevent caching of sensitive responses
response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
response.headers["Pragma"] = "no-cache"
```

### Flag These as Medium

- Missing HSTS
- Short HSTS max-age (< 1 year)
- Missing X-Content-Type-Options
- X-Frame-Options allowing embedding
- Sensitive content without no-store
