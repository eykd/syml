# Spec-Kit Commands with Beads Integration

This directory contains the spec-kit workflow commands integrated with [beads_rust](https://github.com/Dicklesworthstone/beads_rust) for task tracking and workflow orchestration. This workflow was ported from the `turtlebased-ts` project's `/sp:*` commands and retargeted for this Python codebase.

## Architecture: Agent-Backed Commands

Most `/sp:*` commands are **thin wrappers** that delegate to a custom agent in `.claude/agents/`. This provides:

- **Context isolation**: Each phase runs in its own agent context window
- **Model routing**: Opus for creative/security phases, Sonnet for structured/mechanical phases
- **In-session execution**: `/sp:08-harden` runs reviews and dispatches the `/ralph` skill for remediation, all in the user's current session, until a clean cycle

**Exceptions — inline main-session commands**: `/sp:01-brainstorm` and
`/sp:02-specify` run entirely in the main conversation (no agent dispatch) so
they can drive an interactive interview with `AskUserQuestion`. Orchestrator
commands (`/sp:04-red-team`, `/sp:07-implement`, `/sp:08-harden`) also loop in
the main session and use agents only for leaf work, because subagents cannot
spawn subagents.

### Model Assignments

| Phase           | Agent / Components                                                                                                       | Model         | Rationale                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------- | ---------------------------------------------------- |
| 00-constitution | `sp-00-constitution`                                                                                                     | sonnet        | Template-filling                                     |
| 01-brainstorm   | inline (main session, interactive)                                                                                       | main model    | Divergent exploration + requirements                 |
| 02-specify      | inline (main session, interactive)                                                                                       | main model    | Creative spec generation + clarification             |
| 03-plan         | `sp-03-plan`                                                                                                             | opus          | Architectural planning                               |
| 04-red-team     | `sp-04-red-team-pass` + `deepen-plan-loop` (orchestrated in main conv.)                                                  | opus / sonnet | Adversarial analysis interleaved with concretization |
| 05-tasks        | `sp-05-tasks`                                                                                                            | sonnet        | Mechanical task generation                           |
| 06-analyze      | `sp-06-analyze`                                                                                                          | sonnet        | Systematic validation                                |
| 07-implement    | `sp-07-implement` (preflight) + `/ralph` skill (orchestrated in main conv.)                                              | sonnet        | TDD coding                                           |
| 08-harden       | `sp-security-review` / `sp-architecture-review` / `sp-code-quality-review` + `/ralph` skill (orchestrated in main conv.) | opus / sonnet | Iterative review + remediation until clean cycle     |
| next            | `sp-next`                                                                                                                | sonnet        | Lightweight orchestration                            |

**Direct-invoke review commands** (not phase tasks; use ad-hoc for a single review):

- `/sp:security-review` → `sp-security-review` agent (opus)
- `/sp:architecture-review` → `sp-architecture-review` agent (sonnet)
- `/sp:code-quality-review` → `sp-code-quality-review` agent (sonnet)

### Dispatch Flow

```
User types /sp:03-plan → command wrapper loads → $ARGUMENTS substituted
  → main model launches sp-03-plan agent → agent runs with opus model
  → agent completes → result returned to main conversation
```

## Command Reference

| Command               | Description                                                            | Beads Integration                                                       |
| --------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `/sp:00-constitution` | Project constitution management                                        | None                                                                    |
| `/sp:01-brainstorm`   | Explore and capture requirements                                       | None (pre-branch, pre-epic)                                             |
| `/sp:02-specify`      | Create feature specification                                           | Creates epic + all phase tasks                                          |
| `/sp:03-plan`         | Create implementation plan                                             | Closes phase task when done                                             |
| `/sp:04-red-team`     | Adversarial review                                                     | Enhances plan.md, closes phase task                                     |
| `/sp:05-tasks`        | Generate implementation tasks                                          | Creates US tasks under implement phase                                  |
| `/sp:06-analyze`      | Analyze artifacts                                                      | Auto-fixes consistency issues, validates coverage, queries beads status |
| `/sp:07-implement`    | Execute implementation                                                 | Closes self when all sub-tasks done                                     |
| `/sp:08-harden`       | **Iterative review + remediation** (security/arch/quality, with ralph) | Creates remediation tasks; closes self after clean cycle                |
| `/sp:next`            | **Orchestrate workflow**                                               | Queries `br ready`, invokes next command                                |

**Ad-hoc review commands** (not phases; invoke directly when you want a single review):

| Command                   | Description                      | Beads Integration                  |
| ------------------------- | -------------------------------- | ---------------------------------- |
| `/sp:security-review`     | Security review (base..HEAD)     | Creates remediation tasks in beads |
| `/sp:architecture-review` | Architecture review (base..HEAD) | Creates remediation tasks in beads |
| `/sp:code-quality-review` | Code quality review (base..HEAD) | Creates remediation tasks in beads |

## Workflow: Beads Dependency Chain

The entire workflow is driven by beads task dependencies. `/sp:02-specify` creates ALL phase tasks upfront, and each phase closes itself when done to unblock the next.

```text
/sp:01-brainstorm (optional)
     │
     └── Writes requirements doc to specs/brainstorms/
           │
           ▼
/sp:02-specify
     │
     ├── Discovers brainstorm doc (if exists) to accelerate interview
     ├── Creates Epic: "Feature: <name>"
     │
     └── Creates Phase Tasks with Dependencies:
           │
           ├── [sp:03-plan] Create plan
           │         │
           ├── [sp:04-red-team] Adversarial review  ←── depends on 03
           │         │
           ├── [sp:05-tasks] Generate tasks  ←── depends on 04
           │         │
           ├── [sp:06-analyze] Analyze artifacts  ←── depends on 05
           │         │
           ├── [sp:07-implement] Execute implementation  ←── depends on 06
           │         │
           │         ├── US1: User story 1 (sub-task)
           │         ├── US2: User story 2 (sub-task)
           │         └── ...
           │
           └── [sp:08-harden] Iterative review + remediation  ←── depends on 07
                     │
                     │  Loops internally (all in the user's session):
                     │    security review → /ralph drain → architecture review → /ralph drain
                     │      → code-quality review → /ralph drain → restart from security
                     │    Exits when 3 reviews in a row produce zero p1/p2 findings,
                     │    or after a 5-cycle safety cap.

Progress: Run `/sp:next` to query `br ready` and invoke the next phase
```

## Phase Task Naming Convention

Phase tasks use the `[sp:NN-name]` prefix for automatic command invocation:

| Phase Task              | Command Invoked    |
| ----------------------- | ------------------ |
| `[sp:03-plan] ...`      | `/sp:03-plan`      |
| `[sp:04-red-team] ...`  | `/sp:04-red-team`  |
| `[sp:05-tasks] ...`     | `/sp:05-tasks`     |
| `[sp:06-analyze] ...`   | `/sp:06-analyze`   |
| `[sp:07-implement] ...` | `/sp:07-implement` |
| `[sp:08-harden] ...`    | `/sp:08-harden`    |

## Using /sp:next

The `/sp:next` command orchestrates the workflow automatically:

```bash
# Progress to the next ready phase
/sp:next

# Show workflow status without invoking
/sp:next --status

# Skip the current phase and move to next
/sp:next --skip

# Force a specific phase
/sp:next 03-plan
```

## Beads Integration

These commands use beads for task management:

1. **Task Storage**: Tasks stored in beads (`.beads/`) with git-backed persistence
2. **Dependencies**: Phase tasks created with `br dep add` to form the workflow chain
3. **Progress**: Each phase closes itself via `br close` to unblock the next
4. **Queries**: `/sp:next` uses `br ready` to find the next available phase

## Prerequisites

- `br` (beads_rust) installed: install via curl
- Git repository (required for beads)
- Beads initializes automatically on first use via `/sp:02-specify`

## Quick Start

```bash
# Optional: Brainstorm before specifying (explores problem space, writes requirements doc)
/sp:01-brainstorm Add user authentication

# Create a new feature specification (creates epic + all phase tasks)
# If a brainstorm doc exists in specs/brainstorms/, specify will discover and use it
/sp:02-specify Add user authentication

# Progress through the workflow automatically
/sp:next              # Invokes /sp:03-plan
/sp:next              # Invokes /sp:04-red-team
/sp:next              # Invokes /sp:05-tasks
/sp:next              # Invokes /sp:06-analyze
/sp:next              # Invokes /sp:07-implement
# ... repeat /sp:next for each implementation task ...
/sp:next              # Invokes /sp:08-harden (loops review + ralph until clean)

# Or invoke phases directly
/sp:03-plan
# etc.
```

## Checking Task Status

```bash
# View ready tasks (unblocked)
br ready

# View all tasks for a feature epic
br show <epic-id> --json  # use .[0].dependents array for child tasks

# View dependency tree (shows phase chain)
br dep tree <epic-id> --direction up

# Get statistics
br stats

# Check workflow status
/sp:next --status
```

## Red Team Phase (sp:04-red-team)

The red team phase performs **adversarial review** of requirements and design BEFORE implementation. As of the iterative orchestration update, `/sp:04-red-team` also drives `/deepen-plan` automatically: a single invocation alternates deepen-plan and red-team until both converge.

**Purpose**: Strengthen the plan by thinking like an attacker/critic/tester, on a plan that has first been concretized.

**Outer loop** (orchestrated by `.claude/commands/sp/04-red-team.md`, runs in the main conversation):

1. Launch `deepen-plan-loop` (resolves `NEEDS CLARIFICATION` / `TBD` / `TODO` / vague language so the attacker reviews a concrete plan)
2. Launch `sp-04-red-team-pass` (adversarial analysis; up to 3 internal passes)
3. Compare `git rev-parse HEAD` before and after each subagent — both commit iff they modified plan.md
4. Terminate when one full deepen→red-team cycle leaves HEAD unchanged (or after 3 outer iterations as a safety net)
5. Close the `[sp:04-red-team]` beads phase task once at the end

**Inner red-team process** (`sp-04-red-team-pass`):

1. Reviews spec.md and plan.md from adversarial perspective
2. Identifies security gaps, edge cases, performance bottlenecks, accessibility barriers
3. **Enhances plan.md directly** with findings (no separate tasks to triage)
4. Adds sections: Security Considerations, Edge Cases & Error Handling, Performance Considerations, Accessibility Requirements

**Key Distinction**:

- **sp:04-red-team**: Reviews DESIGN (spec.md + plan.md) → Enhances plan.md
- **sp:08-harden** (and its component reviews `/sp:security-review`, `/sp:architecture-review`, `/sp:code-quality-review`): Reviews CODE (git diff) → Creates beads tasks and iterates remediation

**When It Runs**: After sp:03-plan, before sp:05-tasks (so tasks are generated from a deepened, hardened plan)

**Skip If**: Feature is very simple and doesn't benefit from adversarial thinking (`/sp:next --skip`)

## Compound Learning (`/compound`)

The `/compound` command turns session learnings into durable, auto-applying guidance. Knowledge compounds over time — each feature cycle leaves the project smarter.

**When to use**: After solving a tricky bug, fixing review findings, post-morteming an incident, or discovering a non-obvious pattern.

**What it does** (dual-mode, auto-routed):

- **Default — Mode A:** Edits the relevant `.claude/skills/*/SKILL.md` so future invocations of that skill carry the lesson in any project, in any workflow. Targets are picked automatically from skills invoked in the current session and topical matches against the available-skills list.
- **Fallback — Mode B:** Writes a project-local entry to `.specify/solutions/{category}/{slug}.md` (and updates `INDEX.md`) when the learning is bound to this repo's specific tooling/config, or when the user explicitly asks for a solutions-log entry. Both modes can fire for the same learning.

**How it feeds back**:

- Skill edits (Mode A) auto-apply the next time the target skill loads — no search required.
- Solutions docs (Mode B) are searched by `/sp:03-plan` before planning (Phase 0.5), `/sp:04-red-team` before adversarial analysis, and `/sp:08-harden` reviews cross-reference findings.
- Review completion reports suggest running `/compound` when remediation tasks were resolved.

**Key design**: Standalone command, not a numbered phase. Can be invoked at any time — mid-implementation, after review, after incidents.

## Deepen Plan (`/deepen-plan`)

The `/deepen-plan` command enhances the current feature plan with focused research on uncertain sections.

**Note**: `/sp:04-red-team` now invokes `deepen-plan-loop` automatically as the first step of each outer iteration, so you no longer need to run `/deepen-plan` manually before red-team. Standalone `/deepen-plan` remains useful for mid-plan checks — e.g. after editing plan.md by hand, or to concretize before reviewing the plan with a human.

**When to use**: For ad-hoc concretization passes outside the red-team flow. (For the red-team flow, just run `/sp:04-red-team` directly.)

**What it does**:

1. Loads plan.md and identifies sections with "NEEDS CLARIFICATION", "TBD", or vague language
2. Searches `.specify/solutions/` for prior learnings relevant to each uncertain section
3. Researches unknowns and expands sections with concrete implementation details
4. Updates plan.md in place

**Key design**: Idempotent — can be run multiple times. Does NOT create beads tasks or close any phase.

## Code Review (Not Part of sp Workflow)

The `/code-review` skill is available for iterative code review during development, but is **not part of the sp workflow**:

- **`/code-review`** - Reviews Python files directly (auto-discovers or specify files)
  - Use during development for iterative feedback
  - Creates beads tasks for findings under the current epic
  - Runs in background with Haiku model

The sp workflow includes a **final hardening phase** that reviews git diffs (base..HEAD) and iterates fixes:

- **`/sp:08-harden`** — Loops security → architecture → code-quality reviews, drives ralph between each to fix p1/p2 findings, exits on a clean cycle.
- For ad-hoc, single-review use: `/sp:security-review`, `/sp:architecture-review`, `/sp:code-quality-review`.

**Key difference**: `/code-review` reviews files directly for iterative feedback during development, while `/sp:08-harden` iterates reviews + remediation on all branch changes as final validation before merge.

## Python Specifics

This port swaps every TypeScript-specific mechanism in the original workflow for its Python equivalent:

- **Acceptance tests are pytest-bdd, not a TypeScript acceptance pipeline.** Gherkin specs live in `specs/acceptance-specs/US<NN>-<slug>.feature`, with step bindings in `tests/acceptance/test_us<nn>_<slug>.py`. `just acceptance` runs the suite; `just acceptance-missing` prints stub step definitions for any unbound step. An unbound scenario fails with `StepDefinitionNotFoundError` — that's the RED marker the workflow's red/green steps look for.
- **`tools/` is the Python package backing the workflow's scripts**, in place of the original's `.ts` tool scripts: `tools.commit_red` marks a RED commit (invoked as `.venv/bin/python -m tools.commit_red <id>`), `tools.guard_rules` / `tools.pre_tool_use_bash` back the pre-tool-use hook, and `tools.harden_fingerprint` writes `.sp-harden-findings.json` for `/sp:08-harden` (invoked as `.venv/bin/python -m tools.harden_fingerprint --phase <phase> < findings.json`).
- **`just` recipes replace npm scripts**: `just check` (lint + type-check + test), `just fix` (ruff format + ruff check --fix), plus `install`, `test`, `test-coverage`, `lint`, `lint-fix`, `format`, `acceptance`, `acceptance-missing`, `test-all`, and `beads-init`.
- **Skill renames**, each to avoid a collision:
  - `/commit` → `sp-commit`: a personal `~/.claude/skills/commit` would otherwise shadow this project's skill of the same name.
  - `/orchestrator` → `sp-orchestrator`: same personal-skill-shadowing reason.
  - `/security-review` → `security-audit`: `/security-review` is a Claude Code built-in command, not a project skill, so this workflow's own security-review skill needed a distinct name.
  - `typescript-unit-testing` → `pytest-unit-testing`: renamed to name the actual testing stack this project uses.
