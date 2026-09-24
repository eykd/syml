# /sp:07-implement — In-Session Implementation Orchestrator

## User Input

```text
$ARGUMENTS
```

Arguments are optional context. Ralph derives its scope from the current
branch automatically, so no epic argument is required.

## Purpose

Drain the feature epic's ready queue by running the `/ralph` skill **in the
main session**. Ralph runs the prep/verify bookkeeping scripts inline and
dispatches one short-lived `ralph-worker` subagent per task, returning when the
queue is drained.

## Critical: orchestrate in the main conversation

**Run all of the following directly in the main conversation. Do NOT delegate
orchestration to a subagent.** Ralph works by running its prep/verify scripts
inline and dispatching a `ralph-worker` `Agent` per task, and **subagents cannot
spawn subagents** — if this command handed the whole job to an orchestrator
subagent, that subagent could neither dispatch the worker nor persist prep's
beads writes, and ralph would collapse into one long-running inline context. The
preflight (Step 1) is the _only_ part delegated to a subagent; everything else
— invoking ralph, and the completion handling — happens here, in the
user-visible session that ralph treats as its monitor.

(This mirrors `/sp:08-harden`, which orchestrates in the main conversation and
only launches leaf work — the reviews and the ralph drain — from there.)

## Completion signal: side-effects, never the notification envelope

A dispatched subagent's result (the Step 1 preflight block; ralph's per-task
worker replies) arrives in a `<task-notification>`. Decide _what happened_ from
durable side-effects — the preflight **body** contract, ralph's own
"Queue drained" return, and the beads state read in Step 3 (`OPEN_COUNT`) — not
from the notification's `<task-id>` envelope, and never by correlating the
`agentId` returned at launch with a notification id. Notification envelopes have
been observed to mis-attribute (a rest event stamped with a previous agent's
task-id, or a stale-duplicate body) **even with strictly sequential, one-at-a-time
dispatch**. Beads is the source of truth for completion here; the notification
envelope is not.

## Execution Steps

### Step 1 — Preflight (subagent)

Launch the `sp-07-implement` agent via the Agent tool to gather facts:

```
Agent(subagent_type="sp-07-implement", description="sp:07 preflight",
      prompt="Run preflight for /sp:07-implement and return your block.")
```

It returns exactly one block. Dispatch on it:

| Block        | Action                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------- |
| `PROCEED …`  | Store `epicId`. Display the listed ready tasks. Go to Step 2.                                                 |
| `COMPLETE …` | Store `epicId`. No ready tasks and the epic is fully closed. Skip Step 2; go to Step 3 to close out + report. |
| `BLOCKED …`  | Report the wait condition (the listed blockers) to the user and **stop** — nothing is drainable yet.          |
| `NO_TASKS`   | Report: "No beads epic/tasks found. Run `/sp:05-tasks` to create them." and **stop**.                         |

### Step 2 — Drain the queue (ralph, main session)

Invoke the `/ralph` skill **in this session**:

```
Skill skill=ralph
```

The current branch (the feature epic branch) drives ralph's scope detection
automatically — no epic argument needed. Ralph announces the chosen scope on
iteration 1 so the user can `^C` if it picked wrong, then runs the loop
prep (inline) → worker (subagent) → verify (inline), one task per iteration,
until prep reports `QUEUE EMPTY`.

There is no daemon to monitor, no lockfile, no `.ralph-monitor.json`, and no
`ScheduleWakeup` chain. The session itself runs the loop and the user watches
live.

When ralph returns (queue drained), continue to Step 3.

### Step 3 — Completion (main session)

Run directly in the main conversation.

a. Find the implement phase task:

```bash
IMPLEMENT_TASK_ID=$(br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | contains("[sp:07-implement]")) | .id')
```

b. Retire any finished grouping nodes left behind by an interrupted run
(defensive straggler sweep). A run interrupted mid-tick can leave a `US<N>:`
grouping parent open even though all its children closed — prep.sh retires
these incrementally, but if the run stopped between a leaf closing and the next
prep tick, the parent lingers `open` and keeps `OPEN_COUNT > 0`, so the phase
never closes. Before counting, sweep the implement task's direct dependents and
close any that are themselves DONE grouping nodes (all their `parent-child`
children closed), reusing prep's classifier:

```bash
pc_state() {  # LEAF | ACTIVE | DONE
  local s; s=$(br show "$1" --json 2>/dev/null | jq -r '
    [.[0].dependents[]? | select(.dependency_type=="parent-child")] as $pc
    | "\($pc|length) \([$pc[]|select(.status=="closed"|not)]|length)"')
  read -r total open <<<"$s"
  if [ "${total:-0}" -eq 0 ]; then echo LEAF
  elif [ "${open:-0}" -gt 0 ]; then echo ACTIVE
  else echo DONE; fi
}

for id in $(br show "$IMPLEMENT_TASK_ID" --json \
    | jq -r '.[0].dependents[] | select(.status != "closed") | .id'); do
  if [ "$(pc_state "$id")" = "DONE" ]; then
    br close "$id" --reason "grouping node complete (all child tasks closed)"
  fi
done
```

c. Count remaining open sub-tasks under it (after the sweep):

```bash
OPEN_COUNT=$(br show "$IMPLEMENT_TASK_ID" --json | jq '[.[0].dependents[] | select(.status == "open")] | length')
```

d. If all sub-tasks are closed, close the implement phase task:

```bash
if [ "$OPEN_COUNT" -eq 0 ]; then
  br close "$IMPLEMENT_TASK_ID" --reason "All implementation tasks complete"
fi
```

e. Flush any pending `.beads/` state — only when `.beads/` is the _only_ dirty
area:

```bash
if [ -n "$(git status --porcelain .beads/)" ] \
   && [ -z "$(git status --porcelain | grep -v '^...\.beads/')" ]; then
  git add .beads/
  git commit -m "chore(beads): sync state"
fi
```

f. Show the final summary:

```bash
br stats --json
br dep tree <epic-id> --direction up
```

g. If the implement phase closed: report "Implementation complete. Run
`/sp:08-harden` for the review + remediation cycle."

h. If open tasks remain: report the count and suggest next steps — usually,
inspect the failed tasks' beads comments, fix the underlying issue, then
re-run `/sp:07-implement`.

## Error Recovery

- **Authentication failure inside a subagent**: surface to the user — they
  must re-authenticate before re-running.
- **Repeated task failures**: each failure leaves a `FAILED:` comment on the
  task. Review with `br comments list <id>`.
- **No epic found**: verify the epic exists and its title contains the branch
  name (after stripping leading digits).
- **Hot-loop guard fired**: ralph saw the same task twice in a row from prep —
  inspect the task in beads; the worker likely left it half-done.

Note: This command uses beads exclusively for task tracking. Run `/sp:05-tasks`
if beads tasks do not exist.

## Beads Commands Reference

| Action               | Command                                                 |
| -------------------- | ------------------------------------------------------- |
| Get ready tasks      | `br ready --json`                                       |
| Claim task           | `br update <id> --status in_progress`                   |
| Mark complete        | `br close <id> --reason "summary"`                      |
| View task            | `br show <id>`                                          |
| List open tasks      | `br show <epic-id> --json` (filter `.[0].dependents[]`) |
| View statistics      | `br stats --json`                                       |
| View dependency tree | `br dep tree <epic-id> --direction up`                  |

---

Use subagents liberally and aggressively to conserve the main context window —
but never for orchestration itself, only for the per-task leaf work ralph
dispatches.
