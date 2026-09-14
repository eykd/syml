# /sp:08-harden — Iterative Review + Remediation Orchestrator

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input above when deciding orchestrator behaviour. The supported argument forms are:

- empty (or no flags) → start a fresh harden run from state `r8`
- `--resume` → resume from `.sp-harden-state.json` (used after the user manually `^C`'d mid-cycle and wants to continue from the last persisted state)
- `--status` → print current state file contents and exit without doing work
- `--reset` → delete `.sp-harden-state.json` and `.sp-harden-findings.json` and exit (manual recovery)

## Purpose

Loop through three reviews — security, architecture, code quality — and drive ralph between each one to fix any p1/p2 (CRITICAL/MAJOR) findings. A fix in any review re-starts the cycle from security, because a quality fix can introduce a security regression. The orchestrator exits when **three reviews in a row produce zero p1/p2 standalone findings** (a clean cycle). It otherwise runs to real convergence: the backstop ceiling is 10 outer cycles, and a loop that is fixing findings but re-finding them (flapping) stops early via the stall path and asks the principal rather than grinding to the ceiling.

p3 (MINOR) findings are still filed as remediation tasks but do not trigger an implement step or restart the cycle. They remain open for the user to address later.

## State Machine

```
states:  r8 | r9 | r10 | i | done | failed
r8  → run sp-security-review
       if p1+p2 created > 0: state=i, returnTo=r8
       else: state=r9
r9  → run sp-architecture-review
       if p1+p2 created > 0: state=i, returnTo=r8   # restart cycle after fix
       else: state=r10
r10 → run sp-code-quality-review
       if p1+p2 created > 0: state=i, returnTo=r8
       else: state=done   # clean cycle complete
i   → invoke the /ralph skill in this session (synchronous in-session drain)
       on ralph "Queue drained" → state=returnTo, cycleCount++
       on ralph hot-loop or user ^C → state=failed
```

A **stall** is not a state: the ceiling check and the Flap Check pause the machine at its
current state, ask the principal, and then resume, close, or stop per their answer (see
Stall Path). The state file is left untouched so `--resume` still works.

## Execution Steps

Run all of the following directly in the main conversation. Do NOT delegate orchestration to another agent. (Sub-agent calls for the three reviews are launched via the Agent tool; remediation runs via the `/ralph` skill in this session.)

### Step 0 — Argument handling and state load

a. If `--status` is passed: read `.sp-harden-state.json` if present, print its contents and the contents of `.sp-harden-findings.json`, then exit.

b. If `--reset` is passed: delete `.sp-harden-state.json` and `.sp-harden-findings.json` if they exist. Report what was deleted. Exit.

c. If `--resume` is passed: require `.sp-harden-state.json` to exist. If missing, ERROR: "Cannot --resume: no .sp-harden-state.json found. Run /sp:08-harden with no arguments to start fresh." and exit.

d. If no flags: if `.sp-harden-state.json` exists, WARN the user and ask whether to resume or reset. (If user pre-confirmed via context, default to resume.) If file does not exist, initialise:

```json
{
  "state": "r8",
  "returnTo": null,
  "cycleCount": 1,
  "cycleStartHead": "<git rev-parse HEAD>",
  "cumulativeCriticalHigh": 0,
  "epicId": "<from spec.md front matter>",
  "baseBranch": "<resolved per below>",
  "startTime": "<ISO timestamp>",
  "lastTransition": "<ISO timestamp>",
  "fingerprintHistory": []
}
```

`fingerprintHistory` accumulates one entry per completed review, and is the only place
finding identity survives an iteration boundary (`.sp-harden-findings.json` is deleted
before each review and after each ralph drain). Entry shape:

```json
{
  "cycle": 1,
  "phase": "security-review",
  "fingerprints": ["<sha1>", "..."],
  "priorities": [1, 2, 3]
}
```

`fingerprints` and `priorities` are index-aligned with each other and with the review's
`taskIds`. Only p1/p2 entries participate in flap detection (Step 2e) — p3 findings are
re-filed every cycle by design (see Notes), so counting them would stall a healthy run.

Resolve `baseBranch` once at init:

```bash
base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
if [ -z "$base" ]; then
  for candidate in main master; do
    if git show-ref --verify --quiet "refs/heads/$candidate" || git show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
      base=$candidate
      break
    fi
  done
fi
```

Resolve `epicId` from `specs/<branch>/spec.md` front matter (`grep "Beads Epic"` matched against `syml-[a-z0-9]+`). If not found, ERROR and exit.

Write the state file.

### Step 1 — Dispatch on current state

Read `.sp-harden-state.json` and dispatch:

| state  | Go to step |
| ------ | ---------- |
| r8     | Step 2     |
| r9     | Step 3     |
| r10    | Step 4     |
| i      | Step 5     |
| done   | Step 6     |
| failed | Step 7     |

### Step 2 — Run security review (state = r8)

a. Pre-cycle ceiling check: if `cycleCount > 10`, set `termination_reason = "Stalled: hard ceiling of 10 outer cycles reached."` and go to the **Stall Path** (below). The ceiling is a backstop, not the expected exit — convergence or the Step 2e flap check should normally get there first.

b. Delete any stale `.sp-harden-findings.json`.

c. Launch the `sp-security-review` agent via the Agent tool. Prompt (verbatim — forward the user's original $ARGUMENTS so per-feature context propagates):

```
<original $ARGUMENTS>

Context: Called from /sp:08-harden cycle <cycleCount>, state r8.
Write .sp-harden-findings.json per your spec, then commit.
```

d. After the agent returns, read `.sp-harden-findings.json`. Compute:

```
p1p2 = criticalCount + highCount
```

Then append this review's identity record to `fingerprintHistory` in the state file, and
persist it **now** — before any later step deletes `.sp-harden-findings.json` (Steps 2b
and 5d). Those deletions stay as they are; the history lives in the state file:

```
{ cycle: <cycleCount>, phase: <findings.phase>, fingerprints: <findings.fingerprints>, priorities: <findings.priorities> }
```

If a review's findings file predates the `fingerprints` field (an older agent version),
record an empty array and note it in the cycle summary — flap detection degrades to the
ceiling for that cycle rather than erroring.

e. Flap check: run the **Flap Check** (below) against `fingerprintHistory`. If it reports
a stall, go to the **Stall Path**. Otherwise continue to 2f.

f. Update state:

- If `p1p2 > 0`: set `state = i`, `returnTo = r8`. Add `p1p2` to `cumulativeCriticalHigh`. Go to Step 5.
- Else: set `state = r9`. Go to Step 3.

Persist state file. Record the transition timestamp.

### Step 3 — Run architecture review (state = r9)

Identical to Step 2 but with the `sp-architecture-review` agent. Prompt context: `cycle <cycleCount>, state r9`. The `fingerprintHistory` append and the Flap Check (2d/2e) apply here too.

Transitions:

- If `p1p2 > 0`: `state = i`, `returnTo = r8` (restart cycle). Go to Step 5.
- Else: `state = r10`. Go to Step 4.

### Step 4 — Run code-quality review (state = r10)

Identical to Step 2 but with the `sp-code-quality-review` agent. Prompt context: `cycle <cycleCount>, state r10`. The `fingerprintHistory` append and the Flap Check (2d/2e) apply here too.

Transitions:

- If `p1p2 > 0`: `state = i`, `returnTo = r8` (restart cycle). Go to Step 5.
- Else: `state = done`. Go to Step 6.

### Step 5 — Implement remediations (state = i)

a. Verify `returnTo` is set (must be `r8` per the state machine). If null, ERROR.

b. Check whether any ready tasks exist:

```bash
READY_COUNT=$(br ready --limit 0 --json | jq 'map(select(.issue_type != "epic" and (.title | startswith("[sp:") | not))) | length')
```

If `READY_COUNT == 0`, the prior review filed remediations that are all blocked or already closed — treat this as an immediate DONE for the implement step (no work to drain). Skip step 5c.

c. If `READY_COUNT > 0`, invoke the `/ralph` skill **in this session**:

```
Skill skill=ralph
```

Ralph drains synchronously: it runs the prep/verify bookkeeping scripts inline
and dispatches one `ralph-worker` subagent per task, returning control when it
announces "Queue drained" (or when its hot-loop guard fires). No background
process, no `.ralph-drain-result.json`, no ScheduleWakeup chain.

The user can `^C` mid-drain; on the next `/sp:08-harden --resume` the state
file will still be `i` and step 5 will re-run.

d. On normal ralph return: increment `cycleCount` (this completes the outer
cycle). Set `state = returnTo` (always `r8`), `returnTo = null`. Delete
`.sp-harden-findings.json`. Persist state. Recursively continue at Step 1
to start the next cycle's r8 review.

e. On ralph hot-loop or user `^C`: leave `state = i` in the state file so a
subsequent `/sp:08-harden --resume` retries. If the same task keeps
hot-looping across resumes, set `state = failed` and go to Step 7.

### Step 6 — Done (state = done)

a. Close the `[sp:08-harden]` beads phase task:

```bash
HARDEN_TASK_ID=$(br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | contains("[sp:08-harden]")) | .id')
br close "$HARDEN_TASK_ID" --reason "Harden complete: <cycleCount> cycle(s), <cumulativeCriticalHigh> total p1/p2 remediated, HEAD advanced from <cycleStartHead> to $(git rev-parse HEAD)"
```

b. Delete orchestration state files:

```bash
rm -f .sp-harden-state.json .sp-harden-findings.json
```

c. Flush any pending `.beads/` state with the standard guarded gate (only if `.beads/` is the only dirty area).

d. Report to the user:

```markdown
## /sp:08-harden complete

**Cycles run**: <cycleCount> (ceiling 10)
**Termination**: Clean cycle (zero p1/p2 across security, architecture, quality)
**HEAD advance**: <cycleStartHead> → <current HEAD>
**Total p1/p2 remediated**: <cumulativeCriticalHigh>
**Reappeared p1/p2 findings**: <any single reappearances logged by the Flap Check, or "none">

Open p3 (MINOR) tasks may still be present — they were filed but not blocking. Review with `br ready --json | jq '.[] | select(.priority == 3)'`.

**Next steps:** Run `/sp:next` to verify epic completion, or open a PR.
```

### Step 7 — Failed (state = failed)

a. Do **not** close the harden phase task — leave it open for the user to triage.

b. Surface the failure to the user with:

- Current state
- Last transition timestamp
- Failure reason (hot-loop guard message, cycle cap, or user-reported issue)
- Recommended next action: inspect the offending task with `br comments list <id>`, manually unblock it, then resume with `/sp:08-harden --resume`. Or `--reset` to start fresh.

c. Leave `.sp-harden-state.json` in place so the user can resume.

## Flap Check

Run after every `fingerprintHistory` append (Step 2e, and the same step in Steps 3 and 4).

A fingerprint is **flapping** when the same p1/p2 fingerprint appears in two different
`cycle` values in `fingerprintHistory`. It was found, filed, fixed, and found again.

Two properties make this check sufficient without extra machinery:

- **A drain is implied.** `cycleCount` only increments in Step 5d, after a ralph drain
  returns. So two entries with different `cycle` values necessarily have at least one
  drain (`state: i` → `done`) between them, and two findings within one cycle (r8 then
  r9) share a `cycleCount` and correctly do not count as a reappearance.
- **p3 is excluded.** Filter to entries whose aligned `priorities` value is 1 or 2. p3
  findings are re-filed every cycle by design, so including them would flag every healthy
  multi-cycle run.

Thresholds:

- **One reappearance** — record it in the cycle summary (fingerprint, its beads task IDs,
  the cycles it appeared in) and keep going. One re-find can be a legitimately incomplete
  first fix.
- **Two reappearances of the same fingerprint**, **or** any **two distinct fingerprints
  each reappearing once** — report a stall and go to the **Stall Path**.

## Stall Path

Reached from the Step 2a ceiling check or from the Flap Check. The loop is doing work but
not converging, so the principal decides rather than the orchestrator grinding on.

1. Do **not** close the `[sp:08-harden]` beads phase task, and do not auto-create
   remediation tasks.
2. Write a stall report into the cumulative report (the Step 6 template, with the
   termination line replaced): the `termination_reason`, the full cycle history from
   `fingerprintHistory` (cycle, phase, p1/p2 counts), and the specific evidence — each
   flapping fingerprint with its beads task IDs and the cycles it appeared in.
3. Surface it to the principal with `AskUserQuestion` and **wait**. This orchestrator runs
   in the main session (per the CLAUDE.md orchestration rule), so `AskUserQuestion` is
   available. Offer at minimum:
   - **Continue** — run N more cycles (raise the ceiling by N, clear the flap tally for
     the fingerprints the principal accepts as still-in-progress, resume at Step 1).
   - **Accept current state** — go to Step 6 and close the phase task, leaving the
     outstanding findings as open beads tasks.
   - **Abandon** — leave the phase task open and stop for manual investigation.
4. Leave `.sp-harden-state.json` in place either way, so `--resume` works after manual
   triage.

A stall is distinct from `failed` (Step 7): `failed` means the machinery broke
(hot-loop, `^C`, missing prerequisite), a stall means the machinery worked and the work
is not converging.

## Important Invariants

1. **The state file is the source of truth.** Every transition writes it before launching the next sub-agent. If the session is interrupted (e.g., the user `^C`s mid-cycle), `/sp:08-harden --resume` reconstructs intent from the file alone.

2. **Reviews are responsible for writing `.sp-harden-findings.json`.** If a review agent fails to write the file, treat that as `p1p2 = 0` only if it also reported zero findings in its prose summary; otherwise ERROR (do not silently advance). The file's `fingerprints`/`priorities` arrays are index-aligned with `taskIds`; the orchestrator copies them into `fingerprintHistory` and never recomputes them itself. In this repo, `.sp-harden-findings.json` is written by `tools/harden_fingerprint.py` (invoked as `.venv/bin/python -m tools.harden_fingerprint --phase <phase> < findings.json`), not hand-rolled by each review agent.

3. **Cycle restart on any fix.** Per user decision, restart-on-fix is the chosen policy. A quality fix can introduce a security regression; only three clean reviews in a row prove the branch is hardened.

4. **Never modify `.beads/` directly.** All beads state changes go through `br` so its event log stays consistent. Flush-on-terminal mirrors the guard ralph already uses.

5. **Do not commit `.sp-harden-state.json` or `.sp-harden-findings.json`.** They are in `.gitignore` for that reason. The reviews' `/sp-commit` skill calls must not stage them.

6. **Completion signal is file/beads state, never the notification envelope.** A review subagent's result arrives in a `<task-notification>`. Decide pass/fail from the side-effect — `.sp-harden-findings.json` (`criticalCount + highCount`) and beads state — not from the notification's `<task-id>` envelope, and never by correlating the `agentId` returned at launch with a notification id. Notification envelopes have been observed to mis-attribute (a rest event stamped with a previous agent's task-id, or a stale-duplicate body) **even with strictly sequential, one-at-a-time dispatch**. The findings file is authoritative; the prose-summary fallback in Invariant 2 applies **only** when the file is genuinely absent — never prefer a notification body over a present findings file.

## Notes

- The loop runs until it converges. The ceiling of 10 outer cycles is a backstop; in practice convergence happens in 1–3 cycles on a healthy branch, and a non-converging loop is caught earlier by the Flap Check than by the ceiling.
- p3 findings continue to be filed every cycle. This is intentional: the user benefits from a full p3 list to triage post-harden, even though p3 doesn't block the loop.
- For a single ad-hoc review without the loop, use `/sp:security-review`, `/sp:architecture-review`, or `/sp:code-quality-review` directly. Those commands skip the harden state machine entirely.
- If `br ready` returns zero non-epic, non-meta tasks when state is `i`, the orchestrator treats it as immediate DONE — this can happen if a previous run already drained the relevant tasks before harden was re-entered.
