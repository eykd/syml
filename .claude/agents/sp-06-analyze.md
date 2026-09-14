---
name: sp-06-analyze
description: Validate cross-artifact consistency between spec.md, plan.md, and beads tasks. Auto-fixes terminology, coverage gaps, orphan tasks, duplicates. Creates remediation tasks for complex issues.
tools: Read, Grep, Glob, Bash, Edit, Write, Skill
model: sonnet
---

## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across spec.md, plan.md, and beads tasks before implementation. This command MUST run only after `/sp:05-tasks` has successfully produced tasks in beads.

**Additionally**, this command queries beads for task status and progress metrics.

## Relationship with sp:04-red-team

sp:04-red-team and sp:06-analyze serve complementary purposes:

- **sp:04-red-team** (Design Phase): Adversarial review BEFORE task generation
  - Enhances plan.md with security, edge cases, performance, accessibility
  - Prevents problems by strengthening design
  - Thinks like attacker/critic/tester
  - Runs AFTER sp:03-plan, BEFORE sp:05-tasks

- **sp:06-analyze** (Validation Phase): Consistency check AFTER task generation
  - Auto-fixes terminology, coverage gaps, orphan tasks, duplicates
  - Validates requirements → task coverage
  - Enforces constitution principles
  - Creates remediation tasks for complex issues only
  - Provides beads status reporting
  - Runs AFTER sp:05-tasks, BEFORE sp:07-implement

Both phases improve artifacts directly, minimizing manual triaging. Red team makes analyze's job easier by improving input quality.

## Operating Constraints

**AUTO-REMEDIATION FIRST**: This command **MUST** automatically fix consistency issues where possible by editing spec.md, plan.md, and beads tasks directly. Only create remediation beads tasks for complex issues requiring judgment. Do not require explicit user approval for auto-fixes.

Auto-fix classification:

**Safe Auto-Fixes (Apply Immediately):**

- Terminology consistency: Search/replace to standardize terminology across spec.md and plan.md
- Coverage gaps: Auto-generate beads tasks for uncovered requirements
- Partial coverage (fold-in): When a requirement is covered at one layer but a sibling item is missing from an _existing_ open task, fold the missing piece into that task's description in place (`br update --description`) — do NOT defer it to a new task
- Orphan task mapping: Add `**Spec**:` references to task descriptions
- Simple duplicates: Comment out near-identical requirements (>90% text similarity)

**Conditional Fixes (Ask First):**

- Ambiguous terms: Offer to add TODO markers or propose default metrics
- Missing acceptance criteria: Offer to generate criteria from requirement text

**Manual Remediation Tasks (Complex Issues):**

- Constitution violations: Require architectural changes or spec rewrite
- Conflicting requirements: Require user decision on which to keep
- Major underspecification: Require domain knowledge

Task creation rules (for manual remediation only):

**Fold-in first.** Before creating any task, ask: _can this fix be expressed as a
modification to the scope of an existing open task?_ If the fix is "add/modify
content inside a task that already exists" — a missing sibling in a multi-file
task, a scope omission, partial coverage at one layer — apply it in place now via
`br update <id> --description ...`, exactly as you already edit spec.md and
plan.md directly. Only create a standalone task when the fix is genuinely new,
independent work that does not belong inside any existing task. See the fold-in
auto-fix in Step 6.

> **Why this matters.** A remediation task that says "add X to task `.5.2.14`"
> but is merely parented to the epic can never run before `.5.2.14`. Parent-child
> is not a scheduling edge, so the remediation is immediately ready; and a
> HIGH→p2 remediation is drained _after_ the p1 TDD chain it was supposed to
> expand. Fold-in sidesteps the ordering problem entirely.

For each manual finding that genuinely needs a new task:

- First search existing beads tasks under the epic (open + in_progress) to avoid duplicates.
- Only create a new task if no existing task clearly covers the same issue.
- Each created task MUST:
  - Be parented to the current epic
  - Include a concise title starting with `Remediate:`
  - Include a description that cites: impacted artifact(s), severity, and a concrete fix suggestion
  - Include acceptance criteria
- **Wire the task into the dependency graph — parenting to the epic is NOT enough.**
  A `parent-child` edge establishes hierarchy only; it does NOT gate execution
  order (ralph's `br ready` surfaces an epic child the moment nothing _blocks_ it).
  If the remediation must run **before** other work, you MUST add a `blocks` edge:
  - For each existing task `T` that must wait for this remediation `R`, run
    `br dep add <T> <R>` — this reads "`T` depends on `R`", so `T` stays blocked
    until `R` closes. **Argument order is load-bearing: the task that must wait
    comes first.**
  - If the remediation must gate implementation generally, add the blocks edge to
    the relevant `[sp:07-implement]` phase task or user-story parent instead.
  - Use the `/beads-task-chains` skill (Type F: Remediation) to decide placement,
    consistent with `/sp:05-tasks` — do not create the task free-floating.
- Assign priority by severity (CRITICAL → p1, HIGH → p2, MEDIUM → p3) **for triage
  only**. Priority is a triage signal, not an ordering mechanism — within the
  ready set ralph picks the highest priority first, but priority never holds one
  task behind another. A "must-run-before" remediation MUST therefore carry a
  `blocks` edge (above) AND inherit a priority **≥ the highest priority among the
  tasks it blocks**, so it is never starved beneath the work it guards.

You MUST still output a structured analysis report, and include a section listing the remediation tasks you created (IDs + titles).

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit constitution update outside `/sp:06-analyze`.

## Execution Steps

### 1. Initialize Analysis Context

Run `.specify/scripts/bash/check-prerequisites.sh --json` once from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS. Derive absolute paths:

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md

Abort with an error message if spec.md or plan.md is missing (instruct the user to run missing prerequisite command).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

### 2. Retrieve Beads Epic and Task Status

a. Get the epic ID from spec.md:

```bash
grep "Beads Epic" FEATURE_DIR/spec.md | grep -oE 'syml-[a-z0-9]+'
```

b. Query beads for task statistics:

```bash
br stats --json
```

c. List all tasks for this feature:

```bash
br show <epic-id> --json | jq '.[0].dependents'
```

d. Get ready tasks:

```bash
br ready --json
```

e. View dependency tree:

```bash
br dep tree <epic-id> --direction up
```

- Note: `--direction up` shows dependents/children (default `down` shows blockers, which is empty for an epic)

### 3. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From spec.md:**

- Overview/Context
- Functional Requirements
- Non-Functional Requirements
- User Stories
- Edge Cases (if present)

**From plan.md:**

- Architecture/stack choices
- Data Model references
- Phases
- Technical constraints

**From beads tasks** (via `br show <epic-id> --json`, using `.[0].dependents` array):

- Task IDs and titles
- Task descriptions (containing spec refs, skills, acceptance criteria)
- Task hierarchy (parent-child relationships)
- Task status (open, in_progress, closed)
- Dependencies
- Progress metrics

**From constitution:**

- Load `.specify/memory/constitution.md` for principle validation

### 4. Build Semantic Models

Create internal representations (do not include raw artifacts in output):

- **Requirements inventory**: Each functional + non-functional requirement with a stable key (derive slug based on imperative phrase; e.g., "User can upload file" → `user-can-upload-file`)
- **User story/action inventory**: Discrete user actions with acceptance criteria
- **Task coverage mapping**: Map each beads task to one or more requirements or stories using:
  - Explicit `**Spec**:` references in task descriptions
  - Task titles matching user story patterns (e.g., "US1:", "US-1")
  - Keyword inference from task descriptions
- **Constitution rule set**: Extract principle names and MUST/SHOULD normative statements
- **Beads task status**: Map task IDs to their current status (open, in_progress, closed)

### 5. Detection Passes (Token-Efficient Analysis)

Focus on high-signal findings. Limit to 50 findings total; aggregate remainder in overflow summary.

#### A. Duplication Detection

- Identify near-duplicate requirements (>90% text similarity)
- **Auto-fix**: Comment out duplicate in spec.md with note: `<!-- Duplicate of REQ-X; removed by sp:06-analyze -->`

#### B. Ambiguity Detection

- Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria
- Flag unresolved placeholders (TODO, TKTK, ???, `<placeholder>`, etc.)
- **Conditional fix**: Offer to add TODO markers or propose default metrics (ask user first)

#### C. Underspecification

- Requirements with verbs but missing object or measurable outcome
- User stories missing acceptance criteria alignment
- Tasks referencing files or components not defined in spec/plan
- **Conditional fix**: Offer to generate acceptance criteria from requirement text (ask user first)
- **Manual task**: Create remediation task for major underspecification requiring domain knowledge

#### D. Constitution Alignment

- Any requirement or plan element conflicting with a MUST principle
- Missing mandated sections or quality gates from constitution
- **Manual task**: Create CRITICAL remediation task (requires architectural changes)

#### E. Coverage Gaps

- Requirements with zero associated tasks
- **Partial coverage**: A requirement is covered at one layer (e.g., a handler task references it) but a sibling item is missing from an _existing_ multi-file task at another layer (e.g., a use-case TDD pair omits one of the use cases it should cover). This is the most common coverage finding and the easiest to mishandle — it is a scope edit to an existing task, **not** new work.
- Tasks with no mapped requirement/story
- Non-functional requirements not reflected in tasks (e.g., performance, security)
- **Auto-fix for uncovered requirements**: Create beads task with format:
  ```
  Title: Implement [requirement title]
  Description:
  **Spec**: [requirement reference]
  **Context**: Auto-generated from sp:06-analyze coverage analysis
  **Acceptance**: [extract from requirement acceptance criteria]
  ```
  If this task must precede existing work, wire it with a `blocks` edge per the Task creation rules — do not rely on the epic parent to order it.
- **Auto-fix for partial coverage (fold-in)**: Edit the existing open task **in place** to add the missing item — do NOT create a deferred task. A deferred task parented only to the epic cannot reorder itself ahead of the (usually higher-priority) work it must modify, so it runs too late to matter. Because `br update --description` REPLACES the body, read the current description first, merge in the missing item, then write the full text:

  ```bash
  CUR=$(br show <id> --json | jq -r '.[0].description')
  br update <id> --description "$CUR

  **Added by sp:06-analyze (partial-coverage fix):** also cover <missing item>."
  ```

- **Auto-fix for orphan tasks**: Add `**Spec**: [best-match-requirement]` to task description

#### F. Inconsistency

- **Terminology drift**: Use `/glossary` skill to:
  - Check if terms in spec.md, plan.md, and task descriptions match glossary
  - Detect use of synonyms (e.g., "user profile" vs. "user account")
  - **Auto-fix**: Search/replace to standardize to canonical glossary terms
  - Flag prominent names (entities, use cases, value objects) that don't match glossary
  - Report any terms used in domain/application layers not in glossary
- Data entities referenced in plan but absent in spec (or vice versa)
- Task ordering contradictions (e.g., integration tasks before foundational setup tasks without dependency note)
- Conflicting requirements (e.g., one requires whitespace-preserving multiline values while another specifies stripping them)
- **Auto-fix for terminology**: Search/replace to standardize terminology across spec.md and plan.md using glossary as authority
- **Manual task**: Create HIGH remediation task for conflicting requirements (requires user decision)

#### G. Acceptance Spec Coverage

- For each `US<N>` task under `[sp:07-implement]`, verify a corresponding Gherkin feature file exists in `specs/acceptance-specs/`:
  ```bash
  ls specs/acceptance-specs/US*.feature 2>/dev/null
  ```
- Cross-reference: each user story in spec.md with **Acceptance Scenarios** should have a matching `.feature` file and a binding module `tests/acceptance/test_us<nn>_<slug>.py`
- **Auto-fix**: If a feature file or its binding module is missing but spec.md has GWT acceptance scenarios for that story, create them by extracting the scenarios (same format as sp:05-tasks step 6)
- **CRITICAL finding**: If a `US<N>` task exists but has no feature file AND spec.md has no acceptance scenarios for that story, flag as CRITICAL — ralph's ATDD cycle will fail without it
- After creating any missing feature files, run the acceptance suite and confirm each unbound scenario fails with `StepDefinitionNotFoundError` (the RED marker):
  ```bash
  just acceptance 2>&1 || true
  ```

### 6. Apply Auto-Fixes

Before creating manual remediation tasks, apply auto-fixes where safe:

**Safe Auto-Fixes (Apply Immediately):**

1. **Terminology Consistency**: Search/replace to standardize terminology across spec.md and plan.md
   - Example: "user profile" → "user account" (5 occurrences)
   - Log all changes for reporting

2. **Coverage Gaps - Create Missing Tasks**:
   - For requirements with **zero** task coverage, create beads task:
     ```bash
     br create --parent <epic-id> --description "**Spec**: [requirement reference]\n\n**Context**: Auto-generated from sp:06-analyze coverage analysis\n\n**Acceptance**: [extract from requirement acceptance criteria]" "Implement [requirement title]"
     ```
   - If this task must run **before** existing work, also add a `blocks` edge per the Task creation rules (`br dep add <existing-task> <new-task>`). Epic parenting alone will not order it.

3. **Partial Coverage - Fold In** (preferred over creating a task):
   - When a requirement is covered at one layer but a sibling item is missing from an _existing_ open task, edit that task **in place** instead of creating a deferred task. Read the current description, merge in the missing item, write the full body back (`--description` replaces, it does not append):

     ```bash
     CUR=$(br show <id> --json | jq -r '.[0].description')
     br update <id> --description "$CUR

     **Added by sp:06-analyze (partial-coverage fix):** also cover <missing item>."
     ```

   - Log each fold-in for reporting. A deferred "add X to task Y" task cannot reorder itself ahead of the work it modifies (see the Why-this-matters note above), so folding in is the correct mode for this finding class.

4. **Orphan Task Mapping**:
   - Add `**Spec**: [best-match-requirement]` to task descriptions using `br update --description`
   - Log mappings for reporting

5. **Simple Duplicates**:
   - Comment out duplicate requirements in spec.md with: `<!-- Duplicate of REQ-X; removed by sp:06-analyze -->`
   - Keep clearer/more specific version

**Conditional Fixes (Ask User First):**

Use AskUserQuestion tool for ambiguous fixes:

- "Found ambiguous term 'fast'. Fix: (A) Add TODO marker or (B) Propose default 200ms threshold?"
- "Requirement FR-3 lacks acceptance criteria. Auto-generate from requirement text?"

**Manual Remediation Tasks (Complex Issues):**

Only create tasks for issues that cannot be auto-fixed:

- Constitution violations (CRITICAL)
- Conflicting requirements (HIGH)
- Major underspecification (MEDIUM)

### Verify Remediation Ordering (Gate)

After all task creates, fold-ins, and dependency wiring, **prove** the
remediations will be picked up in the right order — do not assume priority did
the job. Re-query the ready set:

```bash
br ready --sort priority --json
```

For each standalone remediation you created, assert:

1. **No "must-run-before" remediation is sitting as a bare epic child** with no
   `blocks` edge — such a task is ready immediately and will run out of order.
2. **Each task the remediation guards is no longer ready ahead of it** — i.e. the
   guarded task is now blocked until the remediation closes.

If either assertion fails, add the missing `blocks` edge (or fold the fix in
instead) before finishing. Include the first ~10 ready entries in the final
report so a human can sanity-check ordering.

### 7. Severity Assignment

Use this heuristic for manual remediation tasks only:

- **CRITICAL**: Violates constitution MUST, missing core spec artifact
- **HIGH**: Conflicting requirements requiring user decision
- **MEDIUM**: Major underspecification requiring domain knowledge

### 8. Produce Compact Analysis Report

Output a Markdown report (no file writes) with the following structure:

## Artifact Analysis Complete

### Auto-Fixes Applied (N fixes)

**Terminology Standardization:**

- Standardized "user profile" → "user account" (5 occurrences in spec.md, 3 in plan.md)

**Coverage Gaps Filled:**

- Created task bd-abc123: "Implement user profile export" (uncovered requirement FR-7)
- Created task bd-abc124: "Add rate limiting to API" (uncovered NFR-2)

**Partial Coverage Folded In:**

- Expanded task bd-abc222 in place to also cover RecordWeeklyReviewReflectionUseCase (FR-018 was referenced but missing from the US40 use-case TDD pair)

**Orphan Tasks Mapped:**

- Mapped task bd-xyz789 to requirement FR-3

**Duplicates Removed:**

- Commented out duplicate requirement at spec.md:L145 (duplicate of FR-4)

### Conditional Fixes (User Approved)

List any fixes that required user approval and were applied.

### Manual Remediation Tasks Created (N tasks)

**Constitution Violations (CRITICAL):**

- Task bd-def456: "Resolve constitution violation in authentication approach"

**Conflicting Requirements (HIGH):**

- Task bd-def457: "Resolve conflict between FR-10 and FR-15"

**Underspecification (MEDIUM):**

- Task bd-def458: "Clarify acceptance criteria for performance requirement"

**Remediation Ordering Check:**

- Confirmed each "must-run-before" remediation carries a `blocks` edge and the tasks it guards are no longer ready ahead of it (see Verify Remediation Ordering gate). First ~10 ready entries: [list]

### Analysis Summary

| ID  | Category    | Severity | Location(s)      | Summary                      | Resolution                          |
| --- | ----------- | -------- | ---------------- | ---------------------------- | ----------------------------------- |
| A1  | Duplication | HIGH     | spec.md:L120-134 | Two similar requirements ... | AUTO-FIXED: Commented out duplicate |

(Add one row per finding; generate stable IDs prefixed by category initial.)

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
| --------------- | --------- | -------- | ----- |

**Constitution Alignment Issues:** (if any - only manual tasks listed)

**Unmapped Tasks:** (if any - only items not auto-fixed)

### 9. Beads Task Status Report

Include a section showing beads task progress:

**Beads Progress Summary:**

| Metric      | Count |
| ----------- | ----- |
| Total Tasks | X     |
| Open        | X     |
| In Progress | X     |
| Closed      | X     |
| Ready Now   | X     |

**Task Hierarchy:**

```text
[Include output from br dep tree]
```

**Ready Tasks:**

- List tasks currently available for work from `br ready`

**Blocked Tasks:**

- List tasks waiting on dependencies

**Metrics:**

- Total Requirements
- Total Tasks
- Coverage % (requirements with >=1 task)
- Ambiguity Count
- Duplication Count
- Critical Issues Count
- **Beads Completion %** (closed / total tasks)

### 10. Provide Next Actions

At end of report, output a concise Next Actions block:

- If CRITICAL manual tasks exist: Recommend resolving before `/sp:07-implement`
- If only auto-fixes applied: User may proceed to `/sp:07-implement`
- If conditional fixes were skipped: Note which issues remain unresolved
- **If tasks are ready in beads**: Suggest running `/sp:07-implement` to start work
- **Review auto-fixes**: Suggest reviewing edited files (spec.md, plan.md) before proceeding

## Operating Principles

### Context Efficiency

- **Minimal high-signal tokens**: Focus on actionable findings, not exhaustive documentation
- **Progressive disclosure**: Load artifacts incrementally; don't dump all content into analysis
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning without changes should produce consistent IDs and counts

### Analysis Guidelines

- **Auto-fix safe issues**: Apply terminology standardization, coverage gaps, orphan mapping, and duplicate removal automatically
- **Ask before conditional fixes**: Use AskUserQuestion for ambiguous fixes where user judgment is needed
- **Create tasks for complex issues**: Only create manual remediation tasks for constitution violations, conflicting requirements, and major underspecification
- **NEVER hallucinate missing sections** (if absent, report them accurately)
- **Prioritize constitution violations** (these are always CRITICAL manual tasks)
- **Use examples over exhaustive rules** (cite specific instances, not generic patterns)
- **Report zero issues gracefully** (emit success report with coverage statistics)
- **Log all changes**: Track every auto-fix applied for the final report

## Beads Commands Reference

| Action          | Command                                       |
| --------------- | --------------------------------------------- |
| Get statistics  | `br stats --json`                             |
| List all tasks  | `br show <epic-id> --json` (dependents array) |
| Get ready tasks | `br ready --json`                             |
| View hierarchy  | `br dep tree <epic-id> --direction up`        |
| Check cycles    | `br dep cycles`                               |

## Commit Changes

Run the `/sp-commit` skill to stage and commit all changes made during this phase. Do not push.

---

You are a subagent: do all work inline in your own context. You cannot dispatch further subagents, so never attempt to delegate — there is no Agent/Task tool available to you.
