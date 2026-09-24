# /sp:04-red-team — Iterative Deepen-Plan + Red-Team Orchestrator

## User Input

```text
$ARGUMENTS
```

You **MUST** forward the user input above verbatim to both subagents on every outer iteration, and consider it yourself when deciding orchestrator behaviour (if not empty).

## Purpose

Drive an **outer iteration loop** that alternates `deepen-plan-loop` and `sp-04-red-team-pass` until one full cycle produces no further changes to **any design artifact** (`plan.md`, `contracts/*`, `data-model.md`). This catches cross-agent second-order effects (deepen-plan resolving uncertainties may open new attack surface; red-team mitigations may introduce new vague language) without the user babysitting the workflow.

**Order each outer cycle**: deepen-plan first, then red-team. Concretize so the attacker has a concrete plan to review.

**Outcome**: a single `/sp:04-red-team` invocation produces a design where the full set of artifacts — `plan.md`, `contracts/*`, and `data-model.md` — is concretized (no `NEEDS CLARIFICATION` / `TBD` / `TODO` / vague language), adversarially hardened (no new Critical/High findings), **and mutually congruent**, with all conditions stable simultaneously. This matters because `/sp:05-tasks` generates tasks from `contracts/` and `data-model.md`; leaving them stale would feed it a design that disagrees with the hardened plan.

## Important Invariant

Convergence relies on each inner subagent committing **iff** it modified **any design artifact (`plan.md`, `contracts/*`, `data-model.md`)**, and not committing when it made no changes. Both `deepen-plan-loop` and `sp-04-red-team-pass` satisfy this via the `/sp-commit` skill, which stages _all_ changes and is a no-op when there are none — so HEAD advances iff the subagent edited any artifact. The orchestrator detects **per-agent change** by comparing `git rev-parse HEAD` before and after each subagent call — if HEAD did not advance, the subagent made no changes. **Termination** is decided one level up, from the artifact content digest (Step 2f/2g): HEAD advances on every commit even when an edit reverts the content to a state seen in an earlier iteration, so content-state comparison is what distinguishes real convergence from a ping-pong stall. Both signals read the same design-artifact set. **This detection is artifact-agnostic and needs no change to cover contracts/data-model: the only thing that widened is which files an agent may edit, not how a commit is detected.** Do not change this invariant without also updating the convergence logic below.

**Completion signal is git HEAD, never the notification.** When a background subagent comes to rest, its report arrives in a `<task-notification>`. Do **not** trust that notification's `<task-id>` envelope or `<result>` body to decide _which_ agent finished or _whether_ it changed anything, and do **not** correlate the `agentId` returned at launch against any notification id. These have been observed to mis-attribute — a rest event stamped with a previous agent's task-id, or a body that is a stale duplicate of the _other_ agent's report — **even with strictly sequential, non-overlapping dispatch** (at most one live agent at a time is not a safeguard). The `pre_*` / `post_*` `git rev-parse HEAD` snapshots below are the **sole** signal for change detection and convergence; the captured `deepen_summary_<N>` / `redteam_summary_<N>` are advisory only (the error abort-check in 2c/2e and the final report). If a HEAD snapshot and a notification body ever disagree, the HEAD snapshot wins.

## Execution Steps

Run all of the following directly in the main conversation. Do NOT delegate this orchestration to another agent.

### Step 1 — Setup

Run `.specify/scripts/bash/check-prerequisites.sh --json` from the repo root and parse the JSON for `FEATURE_DIR`.

- All file paths must be absolute.
- Verify `FEATURE_DIR/plan.md` exists. If not, ERROR: "No plan.md found. Run `/sp:03-plan` first." and stop. Do **not** proceed to Step 3 (phase task close) on error.

Record `branch_start_head=$(git rev-parse HEAD)` for the final report.

Initialise:

- `outer_iteration = 1`
- `outer_summaries = []` (list of `{iteration, deepen_summary, deepen_changed, redteam_summary, redteam_changed}`)
- `artifact_states = []` (ordered list of `{iteration, digest}`)
- `termination_reason = null`

Define the **artifact digest helper** once here and reuse it verbatim in Step 2f. It
digests exactly the design-artifact set the commit-iff-modified invariant covers, and
skips missing files rather than erroring:

```bash
artifact_digest() {
  local files=("$FEATURE_DIR/plan.md")
  [ -f "$FEATURE_DIR/data-model.md" ] && files+=("$FEATURE_DIR/data-model.md")
  [ -d "$FEATURE_DIR/contracts" ] && while IFS= read -r f; do files+=("$f"); done < <(find "$FEATURE_DIR/contracts" -type f | sort)
  git hash-object "${files[@]}" | shasum -a 1 | cut -d' ' -f1
}
```

(Building the array with `[ -f ]` / `find` guards matters: `git hash-object a b c`
aborts at the first missing path, so a bare multi-path invocation would silently drop
every file after an absent `data-model.md`. `find ... | sort` keeps the order
deterministic across iterations.)

Seed the pre-iteration-1 baseline:

```bash
artifact_states=("0:$(artifact_digest)")
```

### Step 2 — Outer Iteration Loop (run until converged, ceiling of 10 outer iterations)

Repeat the following until termination. The loop runs to real convergence; the ceiling
of 10 is a backstop, not a target, and the common case is 1 outer iteration. A loop that
is changing but not progressing is caught by the ping-pong rule in 2g rather than
grinding to the ceiling.

#### 2a. Snapshot HEAD before deepen-plan

```bash
pre_deepen_head=$(git rev-parse HEAD)
```

#### 2b. Launch deepen-plan-loop

Use the Agent tool to launch the `deepen-plan-loop` agent. Prompt:

```
<the original $ARGUMENTS verbatim>

Context: Called from /sp:04-red-team outer iteration <N>. Run one full execution and return your standard report.
```

Capture the returned report into `deepen_summary_<N>`.

#### 2c. Snapshot HEAD after deepen-plan / error check

```bash
post_deepen_head=$(git rev-parse HEAD)
```

If the subagent's report indicates an error (e.g. missing `plan.md`, prerequisite failure), **abort the orchestrator immediately**. Do not run red-team. Do not close the beads phase task. Surface the error to the user and stop.

#### 2d. Launch sp-04-red-team-pass

Use the Agent tool to launch the `sp-04-red-team-pass` agent. Prompt:

```
<the original $ARGUMENTS verbatim>

Context: Called from /sp:04-red-team outer iteration <N>. Run one full execution and return your standard report.
```

Capture the returned report into `redteam_summary_<N>`.

#### 2e. Snapshot HEAD after red-team / error check

```bash
post_redteam_head=$(git rev-parse HEAD)
```

If the subagent's report indicates an error, **abort the orchestrator immediately**. Do not close the beads phase task. Surface the error to the user and stop.

#### 2f. Compute change flags

```
deepen_changed  = (pre_deepen_head    != post_deepen_head)
redteam_changed = (post_deepen_head   != post_redteam_head)
outer_changed   = deepen_changed || redteam_changed
```

Append `{iteration: N, deepen_summary, deepen_changed, redteam_summary, redteam_changed}` to `outer_summaries`.

Also compute the end-of-iteration content state, using the helper defined in Step 1:

```bash
current_digest=$(artifact_digest)
```

The HEAD comparisons above still drive the per-agent summaries; the digest drives
termination.

#### 2g. Termination check

Evaluate in order:

1. If `current_digest` equals the digest of the **last** entry in `artifact_states`: set
   `termination_reason = "Converged: no artifact change this iteration."` and **stop**
   normally (continue to Step 3).
2. Else if `current_digest` matches **any earlier** entry in `artifact_states`: set
   `termination_reason = "Stalled: artifact state returned to iteration <N> (ping-pong)."`
   and **stop via the stall path** (see “Stall Path” below). This is the case git HEAD
   cannot see — HEAD advances on every commit even when the content reverts to a prior
   state, so an A→B→A cycle is invisible to the HEAD comparisons alone.
3. Else if `outer_iteration >= 10`: set `termination_reason = "Stalled: hard ceiling of 10 outer iterations reached."`
   and **stop via the stall path**.
4. Otherwise: append `{outer_iteration, current_digest}` to `artifact_states`, increment
   `outer_iteration`, and continue from Step 2a.

Rule order matters: convergence and ping-pong are both checked before the ceiling, so a
run that converges on iteration 10 reports convergence rather than a stall.

### Stall Path

Reached when Step 2g rule 2 or rule 3 fires — the loop is still changing artifacts but is
no longer making progress. On stall:

1. Do **not** close the `[sp:04-red-team]` beads phase task, and do not auto-create
   remediation tasks. The principal decides what happens next.
2. Write a stall report into the cumulative report (Step 4), in place of the normal
   termination line: the `termination_reason`, the full iteration history, and the
   specific evidence — the repeated artifact digests and which iterations they matched.
3. Surface it to the principal with `AskUserQuestion` and **wait** for an answer. This
   orchestrator runs in the main session (per the CLAUDE.md orchestration rule), so
   `AskUserQuestion` is available. Offer at minimum:
   - **Continue** — run N more outer iterations (raise the ceiling by N and resume at Step 2a).
   - **Accept current state** — close the phase task and finish as if converged.
   - **Abandon** — leave the phase task open and stop for manual investigation.

Then act on the answer. Skip Step 3 unless the principal chose _accept_ (or _continue_
and the resumed loop later converged).

### Step 3 — Close Phase Task

Only reached if Step 2 terminated normally — converged, with no subagent error and no
stall (or a stall the principal resolved by accepting the current state).

a. Read the epic ID from `FEATURE_DIR/spec.md` front matter:

```bash
grep "Beads Epic" $FEATURE_DIR/spec.md | grep -oE 'syml-[a-z0-9]+'
```

b. Find the red team phase task:

```bash
br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | contains("[sp:04-red-team]")) | .id'
```

c. Close the task with a summary including outer-iteration count and branch HEAD advance:

```bash
br close <red-team-task-id> --reason "Iterative red-team complete: <N> outer iteration(s), HEAD advanced from <branch_start_head> to $(git rev-parse HEAD)"
```

Substitute `<N>` and `<branch_start_head>` with their captured values. Do not close the task more than once.

### Step 4 — Cumulative Report

Compute the final uncertainty marker count cheaply, across the **whole design** — `plan.md` plus `contracts/*` and `data-model.md` where they exist — so the reported count reflects every artifact `/sp:05-tasks` will read:

```bash
files=("$FEATURE_DIR/plan.md")
[ -f "$FEATURE_DIR/data-model.md" ] && files+=("$FEATURE_DIR/data-model.md")
[ -d "$FEATURE_DIR/contracts" ] && while IFS= read -r f; do files+=("$f"); done < <(find "$FEATURE_DIR/contracts" -type f)
grep -hcE 'NEEDS CLARIFICATION|TBD|TODO|\b(might|could|possibly|consider)\b' "${files[@]}" | paste -sd+ - | bc
```

(`grep -hc` prints a per-file matching-line count; `paste -sd+ | bc` sums them into a single total. With only `plan.md` present, this collapses to the original single-file count.)

Then output a single markdown report to the user:

```markdown
## Iterative Red Team Complete

**Outer iterations run**: {N} (ceiling 10)
**Termination reason**: {termination_reason — `Converged: …` or `Stalled: …`}
**HEAD advance**: `{branch_start_head}` → `{current HEAD}`
**Artifact state history**: {iteration:digest for each entry in artifact_states, plus the final current_digest}
**Remaining uncertainty markers across plan.md + contracts/\* + data-model.md**: {count}

### Outer Iteration {1}

- **Deepen-plan**: {"no changes" if !deepen_changed else deepen_summary_1}
- **Red-team**: {"no changes" if !redteam_changed else redteam_summary_1}

### Outer Iteration {2}

- ...

### Outer Iteration {N}

- ...

**Next Steps:**

- Review the enhanced plan in `$FEATURE_DIR/plan.md`.
- Run `/sp:next` to proceed to `[sp:05-tasks]`.
```

On a stall, replace the **Next Steps** block with the stall evidence described in the
Stall Path — which digests repeated, which iterations they matched — and do not suggest
`/sp:next`; the phase task is still open.

When a subagent did not advance HEAD on a given outer iteration, render that subagent's row as `"no changes"` rather than its full report (the report is still captured but is redundant when nothing changed). When it did advance HEAD, include the sub-report's headline/summary lines — not the full multi-page output — to keep main-conversation context bounded.

## Notes

- This orchestrator never commits directly. All commits originate from the two inner subagents via the `/sp-commit` skill.
- The `/sp:next` flow that triggers `/sp:04-red-team` is unaffected; `/sp:next` invokes this command by emitting it as the next command from its main-conversation output.
- For a standalone, mid-plan concretization pass without adversarial review, users can still run `/deepen-plan` directly.
