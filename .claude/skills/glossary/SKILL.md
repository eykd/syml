---
name: glossary
description: Track and enforce Ubiquitous Language domain terminology. Use when (1) naming classes/types/functions, (2) detecting naming inconsistencies, (3) reviewing code quality, (4) clarifying domain concepts in specs. Prevents synonyms and ensures naming follows domain conventions.
---

# Glossary Skill

## Purpose

The glossary skill manages the **Ubiquitous Language** for this project - the shared vocabulary used consistently across code, documentation, and discussions. It enforces Domain-Driven Design (DDD) principles by:

1. **Capturing domain terminology** - Tracking business concepts and their precise definitions
2. **Preventing synonyms** - Ensuring each concept has exactly one canonical term
3. **Enforcing consistency** - Validating that code naming matches glossary terms
4. **Supporting workflows** - Integrating with sp:\* commands to maintain language alignment

The glossary is maintained in `docs/glossary.md` as the single source of truth for domain terminology.

## When to Use

### Automatic Usage (Required)

The glossary skill is **automatically referenced** during:

- **Naming classes/types/functions** - Validate names match glossary before creating domain/application layer code
- **Code review** - Check naming quality and consistency (sp:code-quality-review, invoked by /sp:08-harden)
- **Consistency analysis** - Detect terminology drift (sp:06-analyze)
- **Specification** - Identify and clarify domain terms (sp:02-specify)
- **Planning** - Ensure architecture uses canonical terminology (sp:03-plan)

### Explicit Invocation

Call `/glossary` directly when:

- Looking up the definition of a domain term
- Proposing a new term for the glossary
- Requesting a term be renamed/changed
- Checking if a term already exists
- Resolving confusion about terminology

## Entry Format

Each glossary entry follows this concise format:

```markdown
**Term** (part-of-speech): Brief definition (1-2 sentences). [Docs: link] [See: related-term]
```

**Required elements**:

- **Term**: The canonical name in PascalCase (for types/classes) or kebab-case (for concepts)
- **Part of speech**: `(noun)`, `(verb)`, `(adjective)`, etc.
- **Definition**: 1-2 sentences maximum, focused on domain meaning

**Optional elements**:

- `[Docs: path/to/file.md#section]` - Link to detailed documentation (progressive disclosure)
- `[See: other-term]` - Link to related glossary terms

**Examples**:

```markdown
**Use Case** (noun): Application layer orchestrator that implements a single user action by coordinating domain entities and repository interfaces. [See: application-service]

**Entity** (noun): Domain object with persistent identity, defined by ID rather than attributes. [Docs: docs/ddd-clean-code-guide.md#entities] [See: value-object]

**Repository** (noun): Interface defining persistence operations for an aggregate root. [See: aggregate-root]

**Aggregate Root** (noun): An entity that serves as the entry point to an aggregate, enforcing consistency boundaries for a cluster of related objects. [Docs: docs/ddd-clean-code-guide.md#aggregates]
```

**Anti-patterns** (forbidden):

```markdown
<!-- ❌ Multiple terms for same concept (synonyms) -->

**User Profile** (noun): Represents user account data.
**User Account** (noun): Represents user profile data.

<!-- ❌ Definition too verbose -->

**Entity** (noun): A domain object that has a persistent identity that runs through time and different representations. This means that an entity is not defined by its attributes, but rather by a thread of continuity and identity. Two entities with the same attributes may still be different entities if they have different identities. Entities are mutable and can change their attributes over time while maintaining their identity.

<!-- ❌ Missing part of speech -->

**Repository**: Handles persistence for aggregates.

<!-- ✅ Correct: concise, clear, includes POS -->

**Repository** (noun): Interface defining persistence operations for an aggregate root. [See: aggregate-root]
```

## Adding Terms

### Auto-add (General Development)

When working outside sp:\* workflows, **automatically add new domain terms** as you encounter them:

1. **Detect new term**: When creating a class/type/function in domain/application layers, check if the name represents a new domain concept
2. **Draft definition**: Use context from code, comments, or surrounding implementation to create a brief definition
3. **Add to glossary**: Append entry to `docs/glossary.md` in alphabetical order
4. **Continue work**: No user interruption required

**Example flow**:

```
User: "Create a UserProfile entity"
→ Check glossary: "UserProfile" not found
→ Add entry: **UserProfile** (noun): Entity representing user account information including name, email, and preferences.
→ Create class: class UserProfile(Entity[UserProfileId]): ...
```

### Interactive Clarification (sp:\* Workflows)

When working within sp:\* commands, **ask clarifying questions** about new terms like a DDD consultant:

1. **Detect potential term**: Notice a domain concept in user's description
2. **Ask for clarification**: "I notice you're using the term 'X'. Can you clarify what you mean by that in your domain?"
3. **Check for synonyms**: "Is this the same as [similar-term] we defined earlier, or is it different?"
4. **Add user's definition**: Use the user's exact language for the definition
5. **Continue interview**: Proceed with next question

**Example flow** (during sp:02-specify):

```
User: "Users can create campaigns to track their marketing efforts"
Assistant: "I notice you're using the term 'campaign'. Can you clarify what a campaign means in your domain?"
User: "A campaign is a coordinated marketing effort with a specific goal, budget, and timeline"
Assistant: "Got it. I'll add that to the glossary."
→ Add: **Campaign** (noun): A coordinated marketing effort with a specific goal, budget, and timeline.
```

### Checking Before Adding

Always check for similar terms before adding a new entry:

```bash
# Search glossary for similar terms
grep -i "user" docs/glossary.md
grep -i "profile" docs/glossary.md
grep -i "account" docs/glossary.md
```

If a similar term exists, ask the user to clarify the relationship:

- "Is this the same concept?"
- "How is this different from [existing-term]?"
- "Should we use [existing-term] instead?"

## Changing Terms

When a user wants to rename or redefine a term, follow this workflow:

### 1. Find All Usages

Search the codebase for all occurrences:

```bash
# Class/type names (PascalCase)
rg "\bUserProfile\b" --type py

# Function/variable names (snake_case)
rg "\buser_profile\b" --type py

# Documentation references
rg -i "user profile" docs/

# Task descriptions
br list | grep -i "user profile"

# Spec and plan files
rg -i "user profile" .claude/projects/
```

### 2. Generate Refactoring Plan

Provide a comprehensive summary:

```markdown
## Renaming "UserProfile" → "UserAccount"

**Scope**: 23 files, 47 occurrences

### Code Changes

- `src/domain/entities/user_profile.py` → rename file and class
- `src/domain/value_objects/user_profile_id.py` → rename to UserAccountId
- `src/application/use_cases/update_user_profile.py` → rename use case
- 12 other files importing/using UserProfile

### Documentation Changes

- `docs/glossary.md` - update entry
- `docs/architecture.md` - 3 references
- `.claude/projects/*/spec.md` - 2 feature specs

### Task Updates

- 4 beads tasks mention "user profile" in descriptions

### Recommended Approach

1. Use global search/replace for class name (exact match)
2. Manually update file names (git mv)
3. Update import paths
4. Update documentation
5. Update task descriptions via br edit
6. Run tests to verify no breakage
```

### 3. Update Glossary

After renaming is complete:

```markdown
<!-- Option 1: Replace the entry -->

**UserAccount** (noun): Entity representing user account information including name, email, and preferences.

<!-- Option 2: Mark old term as deprecated -->

**UserProfile** (deprecated): See user-account
**UserAccount** (noun): Entity representing user account information including name, email, and preferences.
```

## Synonym Detection

### During Code Review

When reviewing code (sp:code-quality-review, invoked by /sp:08-harden), check for synonym usage:

1. **Extract prominent names**: Find all class/interface/type names in domain/application layers
2. **Compare to glossary**: Check if names match glossary entries
3. **Flag variations**: Detect similar terms that may be synonyms:
   - "UserProfile" vs "UserAccount" vs "Profile"
   - "CreateOrder" vs "PlaceOrder" vs "SubmitOrder"
   - "ProductCatalog" vs "ProductList" vs "Inventory"

4. **Ask for consolidation**: Present findings to user:

   ```
   I found potential synonyms:
   - "UserProfile" (in user_profile_repository.py)
   - "UserAccount" (in user_account_service.py)

   These seem to represent the same concept. Which term should be canonical?
   ```

5. **Update glossary**: Mark canonical term, optionally deprecate others

### Prevention During Development

When adding a new term, **proactively check for potential conflicts**:

```bash
# Check for partial matches
grep -i "profile" docs/glossary.md
grep -i "user" docs/glossary.md

# Check for semantic similarity
# (Look for terms that might overlap in meaning)
```

If potential overlap detected:

- Ask user: "How does this differ from [existing-term]?"
- Suggest: "Should we use [existing-term] instead?"
- Update: If they're the same, use the existing canonical term

### Auto-fix in sp:06-analyze

The sp:06-analyze command includes automatic synonym detection and fixing:

1. **Scan for terminology drift**: Compare spec.md, plan.md, and task descriptions against glossary
2. **Detect synonyms**: Find terms that represent the same concept
3. **Auto-replace**: Use search/replace to standardize to canonical term
4. **Report changes**: Show what was fixed

Example:

```
✓ Fixed terminology drift:
  - Replaced 3 instances of "user profile" with "user-account" in spec.md
  - Replaced 1 instance of "place order" with "create-order" in plan.md
```

## Integration Points

The glossary skill integrates with multiple workflows:

### sp:02-specify (Specification)

- **Interview protocol**: Ask about new domain terms during user interview
- **Validate terminology**: Ensure spec uses glossary terms consistently
- **Capture definitions**: Add user-provided definitions to glossary

### sp:03-plan (Planning)

- **Architecture naming**: Validate that planned classes/types match glossary
- **Interface definitions**: Ensure use case and repository names follow glossary
- **Design review**: Check that design artifacts use canonical terminology

### sp:05-tasks (Task Generation)

- **Task descriptions**: Use glossary terms in task titles and descriptions
- **Consistency check**: Ensure tasks reference domain concepts correctly

### sp:06-analyze (Consistency Analysis)

- **Terminology drift detection**: Find inconsistent term usage
- **Auto-fix synonyms**: Replace non-canonical terms with glossary terms
- **Cross-artifact validation**: Check spec, plan, and tasks align with glossary

### sp:code-quality-review (Code Quality) — invoked by /sp:08-harden

- **Naming validation**: Check class/type/function names against glossary
- **Synonym detection**: Flag potential duplicate terms in new code
- **Prominent name check**: Validate entity/use case/value object names

### Layer-level Development

- **Domain layer**: All entity, value object, and domain service names must match glossary
- **Application layer**: All use case and DTO names should use glossary terminology
- **Infrastructure/Presentation**: Can use technical terms, but domain concepts must match glossary

## Related Skills

- **ddd-domain-modeling**: Defines patterns for entities, value objects, and repositories that glossary terms often represent
- **prefactoring**: Helps choose good names and abstractions, working in tandem with glossary for naming decisions
- **quality-review**: Uses glossary to validate naming quality during code review

## Progressive Disclosure

This SKILL.md provides the core guidance needed for most glossary operations. For detailed patterns and edge cases, see:

- `references/naming-quality.md` - Deep dive on naming quality validation patterns
- `docs/ddd-clean-code-guide.md` - DDD patterns and conventions that glossary terms represent

## Tips for Effective Glossary Use

1. **Start small**: Don't try to capture every term upfront. Add terms as they naturally emerge.
2. **Favor clarity**: A clear 1-sentence definition beats a verbose paragraph.
3. **Link generously**: Use [See: term] and [Docs: link] to connect related concepts.
4. **Be ruthless about synonyms**: One concept = one term, always.
5. **Update eagerly**: When a term evolves, update the glossary immediately.
6. **Review regularly**: During sp:06-analyze, treat glossary validation as a quality gate.

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ Glossary Workflow                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Development Flow:                                          │
│  1. Encounter domain term                                   │
│  2. Check glossary (grep or read)                           │
│  3. If exists: Use canonical term                           │
│  4. If new:                                                 │
│     - sp:* workflow → Ask user for definition               │
│     - General dev → Auto-add with draft definition          │
│  5. Add to glossary alphabetically                          │
│                                                             │
│  Validation Flow (sp:06-analyze, sp:08-harden):             │
│  1. Extract names from code/docs                            │
│  2. Compare against glossary                                │
│  3. Flag mismatches and synonyms                            │
│  4. Auto-fix or report findings                             │
│                                                             │
│  Change Flow:                                               │
│  1. User requests term change                               │
│  2. Find all usages (code, docs, tasks)                     │
│  3. Generate refactoring plan                               │
│  4. Execute changes                                         │
│  5. Update glossary                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
