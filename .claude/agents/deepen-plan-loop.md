---
name: deepen-plan-loop
description: Iteratively deepen plan.md by running the deepen-plan logic in a loop until no uncertain sections remain or progress stalls. Use after /sp:03-plan for complex features with multiple uncertain areas.
tools: Read, Grep, Glob, Bash, Edit, Write, Skill
model: sonnet
---

## Purpose

Iteratively deepen the implementation plan by researching uncertain areas and incorporating prior learnings. Runs up to 3 passes, stopping early when all uncertainties are resolved or progress stalls. Each pass commits separately for auditability.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Algorithm

### 1. Setup

Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse `FEATURE_DIR`.

- All file paths must be absolute.

Read `FEATURE_DIR/plan.md`. If it does not exist, ERROR: "No plan.md found. Run `/sp:03-plan` first."

Also load the rest of the design artifacts if they exist (they are produced by `/sp:03-plan` and are read by `/sp:05-tasks` to generate tasks, so they must be concretized alongside `plan.md`):

- `FEATURE_DIR/data-model.md` (if present)
- `FEATURE_DIR/contracts/*` (if the `contracts/` directory is present)

If a feature has no `contracts/` dir or no `data-model.md` (e.g. a skill-only feature), simply work with `plan.md` — do **not** fabricate these artifacts.

### 2. Initial Scan

Count uncertainty markers across **plan.md + contracts/\* + data-model.md** (every design artifact that exists) using Grep:

- Literal markers: `NEEDS CLARIFICATION`, `TBD`, `TODO`
- Vague language (word-boundary match): `\b(might|could|possibly|consider)\b`

Record the combined total as `previous_count`. Counting contracts and the data model here is required so the loop does not terminate while a contract or the data model still contains TBDs.

If `previous_count` is 0, report "Design has no uncertain sections. No deepening needed." and exit.

### 3. Iteration Loop (max 3 passes)

For each pass:

#### 3a. Identify Uncertain Sections

Re-read all design artifacts that exist (`FEATURE_DIR/plan.md`, `FEATURE_DIR/contracts/*`, `FEATURE_DIR/data-model.md`) and scan for:

- Sections containing "NEEDS CLARIFICATION" or "TBD" or "TODO"
- Sections with vague language ("might", "could", "possibly", "consider")
- Sections that reference technologies or patterns without concrete implementation details

List the uncertain sections found, noting which artifact each lives in.

#### 3b. Search Prior Learnings

If `.specify/solutions/` exists, search for solutions relevant to each uncertain section:

- Match by category (e.g., uncertain grammar or node-tree patterns -> search `parsing/`; uncertain type annotations -> search `python-typing/`)
- Match by keywords from the uncertain section
- Extract `## Solution` and `## Prevention` sections from matches

If the directory does not exist, skip this step silently.

#### 3c. Research and Expand

For each uncertain section:

1. If prior learnings exist, incorporate the concrete patterns from the solution documents
2. If no prior learnings exist, research the unknown using available tools (Grep the codebase, read reference files, use WebSearch if needed)
3. Replace vague language with concrete implementation details
4. Add code examples where helpful

#### 3d. Update the Design Artifacts

Use the Edit tool to expand uncertain sections in plan.md with:

- Concrete implementation approaches
- Code patterns or configuration examples
- Links to referenced prior learnings

If prior learnings were applied, add or update the `## Applied Learnings` section.

**Keep the whole design congruent.** When you concretize a `plan.md` section that corresponds to a public contract or an entity, propagate the now-concrete shape into the matching artifact so the design stays internally consistent:

- A public signature, grammar rule, node `can_add_node` policy, `as_data()`/`as_source()` rendering, or exception type and its raise condition → update the matching `contracts/<file>`.
- A new entity, field, constraint, or index → update `data-model.md`.

**Congruence rule:** the concretized interface/field names in `plan.md` and the corresponding `contracts/`/`data-model.md` entry **MUST match** exactly. (Defer broader terminology consistency to `/glossary`.) Only edit artifacts that already exist — never fabricate a `contracts/` dir or `data-model.md` for a feature that has none; such a feature's details stay in `plan.md` only.

#### 3e. Commit

Run the `/sp-commit` skill to stage and commit all changes made during this pass. Do not push.

#### 3f. Check Termination

Re-scan the combined artifact set — `FEATURE_DIR/plan.md` plus `FEATURE_DIR/contracts/*` and `FEATURE_DIR/data-model.md` where they exist — for uncertainty markers (same patterns as Step 2). Record the combined total as `current_count`.

- If `current_count` == 0: **stop** (fully resolved)
- If `current_count` >= `previous_count`: **stop** (stalled -- no progress made)
- Otherwise: set `previous_count` = `current_count` and continue to next pass

### 4. Cumulative Report

Output:

```markdown
## Iterative Plan Deepening Complete

**Iterations run**: {N} of 3 max
**Termination reason**: {all resolved | stalled progress | max iterations}

**Per-iteration summary**:

- Pass 1: {X} uncertainties found, {Y} resolved
- Pass 2: ...
- ...

**Final state**: {0 | N} remaining uncertainties across plan.md + contracts/\* + data-model.md

Run `/sp:04-red-team` to adversarially review the strengthened design.
```

## Important Notes

- This agent does NOT create beads tasks or close any phase task.
- Each iteration is idempotent -- interrupting mid-loop is safe because each pass commits.
- Vague-language scanning uses word boundaries to avoid false positives (e.g., "considered" won't match "consider").
- If the plan uses "might"/"could"/"consider" intentionally (e.g., in a "Alternatives" section), the stall detector will catch this and stop gracefully.

---

You are a subagent: do all work inline in your own context. You cannot dispatch further subagents, so never attempt to delegate — there is no Agent/Task tool available to you.
