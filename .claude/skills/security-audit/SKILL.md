---
name: security-audit
description: Review code for security vulnerabilities and best practices. Use when (1) reviewing code for security issues, (2) auditing authentication/session handling, (3) checking for XSS/CSRF/SQL injection vulnerabilities, (4) evaluating security headers and CSP, (5) validating input handling and output encoding, (6) assessing password hashing and secrets management, (7) reviewing rate limiting and brute force protection, or (8) general security hardening — including untrusted-input handling, recursion depth, ReDoS, and file handling in a parsing library.
---

# Security Review Skill

Systematic security review following OWASP guidelines and defense-in-depth principles.

## Audience: Non-Technical Managers

**CRITICAL**: Write for non-technical managers using plain English (6th-grade reading level).

**Style Requirements:**

- **Report problems only** - never acknowledge what's done well or include praise
- **Target 30-second scan time** - compress findings to 2-3 lines maximum
- **Use plain language** - explain technical terms briefly (e.g., "SQL injection - inserting malicious database commands")
- **Focus on business impact** - data breach, financial loss, reputation damage
- **Be concise** - one-sentence problem, one-line fix

## Review Process

1. **Identify security surface**: Authentication, data handling, user input, external APIs
2. **Check each domain** using references below
3. **Prioritize findings**: Critical > High > Medium > Low
4. **Provide actionable fixes** with code examples

## Security Domains

### Authentication & Sessions

See [references/auth-security.md](references/auth-security.md) for password hashing (Argon2id), session management (`__Host-` cookies), account lockout, constant-time comparisons.

### Web Security (XSS/CSRF/Headers)

See [references/web-security.md](references/web-security.md) for XSS prevention, CSRF tokens, Content Security Policy, security headers.

### Data Security (Injection/Validation)

See [references/data-security.md](references/data-security.md) for SQL injection prevention, input validation, parameterized queries.

### Quick Checklist

See [references/checklist.md](references/checklist.md) for rapid security audit.

## Critical Patterns to Flag

### Always Critical

```python
# SQL Injection - string interpolation
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")  # ❌
# Missing output encoding
f"<div>{user_input}</div>"  # ❌ (without html.escape)

# Weak password hashing
bcrypt.hashpw(password, salt)  # ❌ Use Argon2id
hashlib.md5(password)  # ❌
hashlib.sha256(password)  # ❌ (no salt)

# Hardcoded secrets
API_KEY = "sk-abc123..."  # ❌

# Unbounded recursion driven by attacker-controlled nesting depth
def incorporate_node(tip, node):  # ❌ no depth limit
    return incorporate_node(tip.parent, node)

# Catastrophic backtracking in a grammar/regex terminal
re.compile(r"(\s*)+:")  # ❌ nested quantifier over attacker-controlled input
```

### Always High

```python
# Reading untrusted input without a size limit
text = untrusted_stream.read()  # ❌ unbounded — memory exhaustion

# Timing-vulnerable comparisons
if token == stored_token:  # ❌ (use hmac.compare_digest)
    ...

# Echoing an attacker-controlled filename straight into logs
logger.info(f"parsed {filename}")  # ❌ (may contain control chars)

# Missing rate limiting on auth endpoints (web-application context)
app.post("/login", handler)  # ❌
```

## Secure Patterns

### Safe HTML Templating

```python
import html

encoded = html.escape(user.name, quote=True)
rendered = f"<div>{encoded}</div>"  # ✅ Explicitly encoded
```

### Parameterized Queries

```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))  # ✅
```

### Bounded Recursion With a Typed Error

```python
MAX_NESTING_DEPTH = 500


def incorporate_node(tip, node, depth: int = 0):
    if depth > MAX_NESTING_DEPTH:
        raise ParseError(f"exceeded max nesting depth ({MAX_NESTING_DEPTH})")
    # ✅ explicit depth counter, typed error instead of RecursionError
    ...
```

### Constant-Time Compare

```python
import hmac


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)  # ✅
```

## Review Output Format

**COMPRESSED FORMAT** (2-3 lines per finding):

```markdown
## Security Review

### Critical

- src/syml/parsers.py:45: unbounded recursion on nested list/mapping depth
  Fix: Add an explicit depth counter that raises `ParseError` past a limit

- src/syml/nodes.py:12: catastrophic backtracking risk in a regex terminal
  Fix: Replace nested quantifier `(\s*)+` with a single bounded `\s*`

### High

- src/syml/parsers.py:23: `syml.loads` has no documented input size limit
  Fix: Document the caller's responsibility to bound input size

### Medium

- src/syml/basetypes.py:34: error message embeds raw `filename` unsanitized
  Fix: Strip control characters before the value reaches logs/terminals

## Copy-Paste Prompt for Claude Code

**REQUIRED when findings exist** (3-5 lines maximum):
```

Add a depth limit to incorporate_node in src/syml/parsers.py:45, raising
ParseError past MAX_NESTING_DEPTH instead of RecursionError.
Fix the regex terminal in src/syml/nodes.py:12 to remove nested quantifiers.
Document the input-size contract for syml.loads in src/syml/parsers.py:23.

```

```

**DO NOT include:**

- ~~"None found"~~ sections - omit sections with no issues
- ~~Praise or positive feedback~~ - focus exclusively on problems
- ~~Lengthy explanations~~ - keep to 2-3 lines per finding

## Parser-Library-Specific Checks

### Untrusted Input & Resource Limits

- No unbounded `read()` of untrusted input before parsing
- Recursive tree-building (`incorporate_node`, multiline value accumulation)
  has an explicit depth limit and raises a typed `ParseError`
- Regex terminals in the Parsimonious grammar are free of nested quantifiers
  and ambiguous alternation that could cause catastrophic backtracking

### File Handling

- `filename` is treated as advisory metadata only, never re-derived into a
  filesystem path by the library
- Error messages embedding `filename` don't let attacker-controlled strings
  inject control characters into logs/terminals

## Related Skills

This skill works together with:

- **quality-review**: Code correctness, test quality, general code standards
- **clean-architecture-validator**: Layer boundaries, architectural compliance
- **ddd-domain-modeling**: Validation architecture, input sanitization

When reviewing code, use multiple skills for comprehensive analysis:

1. **Security audit** (this skill): Untrusted input, resource limits, secrets, error disclosure
2. **Architecture review**: Layer violations, dependency issues
3. **Quality review**: Error handling, test coverage, code standards
