# /sp:shepherd — Workflow Shepherd

## User Input

```text
$ARGUMENTS
```

Optional. If present, treat it as the feature description (when no spec exists
yet) or as context to pass through to the phase commands.

## Purpose

Drive a feature through the whole `sp:*` workflow, phase by phase, until the
epic is complete or a phase blocks. This command is the loop; `/sp:next` is one
step of it.

## Critical: shepherd in the main conversation

Run this loop **here, in the main session. Do NOT delegate it to a subagent.**
`/sp:next` claims a beads task and invokes a phase command, and several phases
(`/sp:07-implement`, `/sp:08-harden`) dispatch `ralph-worker` subagents of their
own. **Subagents cannot spawn subagents**, so a delegated shepherd could neither
dispatch those workers nor persist its beads writes.

Invoke the `/sp-orchestrator` skill for how to delegate — but apply it to the
_leaf_ work each phase performs, never to this loop or to the phase commands
themselves.

## Execution Steps

### Step 0 — Ensure a spec exists

Check for an active feature spec (a `specs/<NNN>-<name>/spec.md` matching the
current branch, and an open beads epic for it).

If none exists, work with the principal to create one before looping:

1. `Skill(skill="sp:01-brainstorm")` — shape the idea
2. `Skill(skill="sp:02-specify")` — write the spec and create the epic

Both are conversational. Ask one question at a time and wait for the answer.

### Step 1 — Take one step

```
Skill(skill="sp:next")
```

`/sp:next` identifies the next ready phase via its read-only preflight agent,
claims the task, and invokes that phase command in this session. Pass through
any relevant `$ARGUMENTS` context.

### Step 2 — Decide whether to continue

After the phase command returns, re-run Step 1. Keep looping while `/sp:next`
reports a `PHASE` block and the phase completes cleanly.

**Stop and report to the principal when any of these happens:**

| Condition                                            | Action                                                              |
| ---------------------------------------------------- | ------------------------------------------------------------------- |
| `/sp:next` reports `COMPLETE`                        | Report the workflow finished; suggest closing the epic.             |
| `/sp:next` reports `BLOCKED` or `NO_EPIC`            | Report the blocker verbatim and stop.                               |
| `/sp:next` reports `ERROR`                           | Surface the reason and stop.                                        |
| A phase command fails or reports open findings       | Report what failed; do not advance to the next phase.               |
| A phase needs a decision only the principal can make | Ask, wait for the answer, then resume the loop.                     |
| The same phase comes back ready twice in a row       | Hot-loop guard: stop and inspect, the phase did not close its task. |

Never skip a phase on the principal's behalf. `/sp:next --skip` exists for that
and requires their explicit request.

### Step 3 — Report

When the loop ends, summarize: which phases ran, which phase stopped it and why,
and the concrete next action. Verify from durable state (`br stats --json`,
`br dep tree <epic-id> --direction up`) rather than from the phase commands'
own summaries.

## Phase Sequence

`01-brainstorm` → `02-specify` → `03-plan` → `04-red-team` → `05-tasks` →
`06-analyze` → `07-implement` → `08-harden`

Phases 03 through 08 are driven by `/sp:next` from the beads phase tasks; 01 and
02 are conversational and run in Step 0.

## Example Usage

```bash
/sp:shepherd                        # continue the current feature to completion
/sp:shepherd add passkey login      # start a new feature from a description
```
