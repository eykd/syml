---
name: compound
description: Use when (1) a session uncovers a non-obvious pattern, gotcha, or workaround; (2) a tricky bug or test failure is resolved; (3) sp:* review remediation completes; (4) a production incident is post-mortemed. Default action: edit the relevant `.claude/skills/*/SKILL.md` so the lesson auto-applies on future invocations. Falls back to `.specify/solutions/` for project-specific gotchas.
---

# Compound Learning Skill

Capture durable lessons where they will fire automatically next time. Real compounding happens when a learning lives inside the skill it pertains to — a gotcha baked into `/pytest-unit-testing` auto-applies every future time that skill loads, in any project, in any workflow. A note in `.specify/solutions/` only fires when something explicitly searches it.

## When to Use

Triggers (any of):

- A session surfaced a non-obvious pattern, anti-pattern, or workaround worth carrying forward.
- A bug, test failure, or surprising build/runtime behavior was diagnosed and fixed.
- A production incident was post-mortemed.
- Review remediation (sp:08-harden) resolved findings worth preserving.
- The user explicitly asks to capture a learning ("compound this", "save this lesson").

Standalone — invoke at any point, in any workflow.

## Two Modes

| Mode  | What it does                                               | When it fires                                                 |
| ----- | ---------------------------------------------------------- | ------------------------------------------------------------- |
| **A** | Edit a `.claude/skills/*/SKILL.md` (default)               | Lesson generalizes — any project using the same tech benefits |
| **B** | Write `.specify/solutions/{category}/{slug}.md` (fallback) | Project-specific tooling/config quirk, or user requests it    |

Both can fire when a learning generalizes AND the incident details are worth preserving — A is never skipped just because B was written.

### Decision: Mode A, Mode B, or both?

| Learning type                                                       | Mode                         |
| ------------------------------------------------------------------- | ---------------------------- |
| Pattern that applies in any project using the same tech             | A                            |
| Anti-pattern, gotcha, or rule of thumb tied to a skill's domain     | A                            |
| Project-specific tooling quirk (ralph, this repo's justfile/pyproject config) | B                            |
| Incident worth preserving symptoms+context for, AND it generalizes  | A + B                        |
| User says "log this to solutions" / "save the incident details"     | B (also A if it generalizes) |

---

## Mode A — Skill Update (default)

### Step 1: Identify candidate skills (no user questions)

Pick 1–3 highest-fit skill targets using these signals, in order:

1. **Primary signal — invoked this session.** Skills the assistant actually called via the `Skill` tool earlier in this conversation. The lesson almost certainly belongs to one of them.
2. **Secondary signal — topical match.** Scan the available-skills list (delivered in system reminders); match skill names and descriptions against the learning's topic keywords.
3. **Tertiary signal — domain area.** If the learning is about testing, the targets cluster around `pytest-unit-testing` / `pytest-coverage`. If about the grammar, around `parsing` / `spec-conformance`. Etc.

Rank by fit. Document the rationale in the report at Step 7 so the user can redirect.

### Step 2: Read the target

Read `.claude/skills/{name}/SKILL.md` and any obviously-relevant file under `references/`. You need the existing structure before deciding where the new line goes.

### Step 3: Find the right home

Prefer extending an existing section over creating a new one. In rough priority:

1. Existing decision table or anti-patterns list → add one row/bullet.
2. Existing "Quick Wins / Avoid These / Common Pitfalls" section → add one bullet.
3. Existing topical heading that matches → add a short paragraph or row.
4. No fit → add a new "## Known Gotchas" section near the bottom (above any "Detailed References" section).

### Step 4: Distill to a durable line

Strip session-specific framing ("the bug we hit on 2026-05-07", "this PR", "the failing test in `test_foo.py`"). Write it as a future-applicable rule, anti-pattern, or trigger.

- One line preferred. One short paragraph maximum.
- Frame as the rule first, then the reason: `Wrap third-party HTTP clients in an adapter before mocking — direct mocks hide internal error paths from coverage.`
- If a learning contradicts existing skill guidance, **fix the contradiction** rather than adding a footnote.
- Never duplicate guidance that's already in the target skill.

### Step 5: Respect the 500-line budget

If the addition would push SKILL.md over ~500 lines (per `skill-improver` best practices), put detail in `.claude/skills/{name}/references/{slug}.md` and keep a one-liner pointer in SKILL.md.

### Step 6: Show the diff before writing

Print the proposed edit (target file, target section, exact new line/block). Get user approval. Then apply via `Edit`.

### Step 7: Consider the description

If the learning exposes a trigger that the target skill's `description:` frontmatter doesn't cover (e.g., the skill should fire in a context it currently doesn't advertise), propose a description update too. Same diff-then-apply flow.

---

## Mode B — Solution Doc (project-specific or on request)

Fires when:

- The user explicitly asks for a solutions-log entry.
- The learning is bound to this repo's specific tooling/config and won't generalize (e.g., "ralph epic detection breaks on numeric branch prefixes in this monorepo's naming scheme").
- The session lacks a clean skill home AND the learning is not project-specific enough to drop.

Output: `.specify/solutions/{category}/{slug}.md` and an INDEX.md update.

### Step B1: Identify the problem

Use what's already in context. If thin, gather:

- Recent git history (`git log --oneline -10`, `git diff HEAD~1..HEAD`).
- Recently closed beads remediation tasks.
- User's description, if any.

If still unclear, ask once: "What problem did you just solve? Describe the symptoms or error you encountered."

### Step B2: Extract the four facts

- **Problem**: symptoms, error messages.
- **Root cause**: the underlying issue.
- **Solution**: concrete steps, code patterns, config changes.
- **Prevention**: how future planning/review/implementation can avoid it.

### Step B3: Auto-categorize

| Category              | Covers                                                |
| --------------------- | ----------------------------------------------------- |
| `python-typing/`      | mypy strictness, annotation gaps, `Source`/basetypes typing quirks |
| `ruff/`               | Lint/format rule conflicts, preview-mode gotchas, pydocstyle `D` rules |
| `pytest-coverage/`    | 100% coverage patterns, `# pragma: nocover`/`nobranch`, fixture typing |
| `parsing/`            | Parsimonious PEG grammar quirks, line-oriented lexing, tree-building edge cases |
| `spec-conformance/`   | SYML-SPECIFICATION.md vs. shipped-parser gaps and conformance findings |
| `security/`           | Input validation, untrusted-input parsing hazards                  |
| `clean-architecture/` | Layer violations, dependency direction, node/visitor design         |
| `tooling/`            | `uv`/`just` recipe quirks, pre-commit hooks, dependency conflicts   |

Suggest the category, let the user override.

### Step B4: Generate the solution document

Format:

```markdown
# {title}

**Category**: {category}
**Date**: {YYYY-MM-DD}
**Feature**: {branch} (optional)
**Tags**: {tag1}, {tag2}

## Problem

{Symptoms and error messages}

## Root Cause

{Why it happened}

## Solution

{Concrete steps, code patterns, or config changes}

## Prevention

{How to avoid this — spec checklist items, plan considerations, review criteria}

## Related

- {links to related solutions}
```

Slug: lowercase kebab-case, max 50 chars. Example: "Parsimonious grammar rule shadows a sibling rule" → `parsimonious-rule-shadows-sibling`.

### Step B5: Write the file

```bash
mkdir -p .specify/solutions/{category}
```

Write to `.specify/solutions/{category}/{slug}.md`. Verify.

### Step B6: Update INDEX.md

Append under the matching `## Solutions` category heading in `.specify/solutions/INDEX.md`:

```markdown
### {category}

- [{title}]({category}/{slug}.md) — {one-line summary} ({date})
```

Create the heading if absent.

---

## Both modes — linking

When both A and B fire for the same learning, the skill edit can end with a pointer:

```
See `.specify/solutions/{category}/{slug}.md` for the original incident context.
```

Keep the line in SKILL.md self-contained — the pointer is supplementary, not the meat.

---

## Report

Output after the work is done:

```markdown
## Learning Captured

**Mode**: {A | B | A + B}

**Skill edits** (Mode A):

- `.claude/skills/{name}/SKILL.md` — added to section "{section}": "{one-line summary of the new content}"
- (target rationale: {invoked-this-session | topical match on {keywords}})

**Solution doc** (Mode B):

- `.specify/solutions/{category}/{slug}.md`
- Indexed in `.specify/solutions/INDEX.md`

**Prevention tip**: {one-line summary}
```

Drop sections that don't apply. If only Mode A fired, the solution-doc block is omitted entirely.

## Guidelines

- **Prefer skill edits over solution docs.** Skill edits compound; solution docs only fire when searched.
- **One new line beats a new section.** Extend, don't expand.
- **Never duplicate existing skill guidance.** If it's already there, you're not learning anything new — close out.
- **Fix contradictions, don't add footnotes.** If a learning conflicts with existing guidance, the existing guidance is wrong or stale; update it.
- **Distill ruthlessly.** Future-applicable rule, not session-specific narrative. Strip dates, branch names, file paths.
- **Show the diff first.** Always preview skill edits before applying.
- **Pick targets, don't ask.** The model identifies candidate skills automatically; the user can redirect after seeing the report.
- **One solution per Mode B doc.** Don't combine unrelated issues.
- **Keep the Prevention section sharp.** That's the part future review/planning phases reference.
