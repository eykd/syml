---
name: clean-architecture-validator
description: 'Use when: (1) reviewing code for architecture compliance, (2) finding dependency violations, (3) validating layer boundaries, (4) checking interface placement, (5) refactoring for better separation.'
---

# Clean Architecture Validator

Analyze code for Clean Architecture compliance focusing on the dependency rule: dependencies point inward, never outward.

## Style Requirements

**CRITICAL**: Write for non-technical managers using plain English (6th-grade reading level).

- **Report problems only** - never acknowledge what's done well or include praise
- **Target 30-second scan time** - compress findings to 2-3 lines maximum
- **Use plain language** - briefly explain technical terms
- **Focus on fixes** - one-sentence problem, one-line fix
- **Conditional sections** - only show sections with violations

## Layer Hierarchy (Inner to Outer)

```
Domain → Application → Infrastructure/Presentation
```

- **Domain**: Entities, Value Objects, Domain Services, Repository Interfaces
- **Application**: Use Cases, DTOs, Application Services
- **Infrastructure**: Repository Implementations, External APIs, Caches
- **Presentation**: Handlers, Controllers, Templates, UI

## The Dependency Rule

Inner layers must never depend on outer layers:

- Domain: Zero external dependencies (no framework imports, no infrastructure)
- Application: Depends only on Domain
- Infrastructure/Presentation: May depend on Application and Domain

## Analysis Workflow

1. **Map the codebase** - Identify layer boundaries from directory structure
2. **Scan imports** - Check each file's imports against allowed dependencies
3. **Classify violations** - Categorize by severity and type
4. **Report findings** - Present violations with refactoring suggestions

## Quick Violation Checks

**Domain layer violations** (most severe):

- Imports from `infrastructure/`, `presentation/`, framework packages
- Direct database/HTTP/file system calls
- Concrete repository implementations instead of interfaces

**Application layer violations**:

- Imports from `infrastructure/`, `presentation/`
- Direct infrastructure instantiation
- Framework-specific types in use case signatures

**Interface misplacement**:

- Repository interfaces in `infrastructure/` (should be in `domain/interfaces/`)
- Port interfaces outside domain layer

## Output Format

**COMPRESSED FORMAT** (2-3 lines per finding):

```markdown
## Architecture Review

### Critical

- src/syml/nodes.py:5: Domain imports infrastructure - violates dependency rule
  Fix: Move file-system logic to an infrastructure-side helper

- src/syml/nodes.py:12: Domain imports an external API client
  Fix: Define a port/interface in domain, implement it in infrastructure

### High

- src/syml/parsers.py:12: Instantiates a concrete implementation directly
  Fix: Accept the dependency via constructor injection

### Medium

- src/syml/basetypes.py:1: Interface defined outside the domain layer
  Fix: Move the interface next to the domain types it describes

## Copy-Paste Prompt for Claude Code

**REQUIRED when findings exist** (3-5 lines maximum):
```

Move file-system logic out of src/syml/nodes.py:5 into an infrastructure helper.
Define a port interface in domain, implement it in infrastructure.
Use constructor injection in src/syml/parsers.py:12.
Move the interface out of src/syml/basetypes.py:1 into the domain layer.

```

```

**DO NOT include:**

- ~~"None found"~~ sections - omit sections with no violations
- ~~Praise or positive feedback~~ - focus exclusively on problems
- ~~Lengthy explanations~~ - keep to 2-3 lines per finding

## Related Skills

This skill works together with:

- **security-audit**: Untrusted input, resource limits, secrets
- **quality-review**: Code correctness, test quality, general code standards
- **ddd-domain-modeling**: Entity design, value objects, repository interfaces

When reviewing code, use multiple skills for comprehensive analysis:

1. **Architecture review** (this skill): Layer violations, dependency issues
2. **Security audit**: Untrusted input, recursion/ReDoS, secrets, error disclosure
3. **Quality review**: Error handling, test coverage, code standards

## References

- **Detailed violation patterns**: See [references/violations.md](references/violations.md)
- **Layer rules and examples**: See [references/layer-rules.md](references/layer-rules.md)
