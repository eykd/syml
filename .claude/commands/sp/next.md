# /sp:next — Workflow Phase Router

## User Input

```text
$ARGUMENTS
```

Optional. Recognized: `--status`, `--skip`, or a phase name (e.g. `03-plan`).

## Purpose

Find the next ready spec-kit phase and run it. A read-only `sp-next` subagent
identifies the phase; **this command** performs the beads writes and invokes the
phase, in the main session.

## Critical: identify in a subagent, invoke here

Most phases are themselves subagents (`sp-03-plan`, `sp-05-tasks`, …) or
orchestrators that dispatch subagents (`/sp:07-implement`, `/sp:08-harden`), and
**subagents cannot spawn subagents**. So `sp-next` only reports; the invocation
and every `br update` / `br close` happen here, in the user-visible session.

Dispatch on the **body** the agent returns — the block below — never on the
`<task-notification>` envelope or a returned `agentId`.

## Execution Steps

### Step 1 — Identify the next phase (subagent)

```
Agent(subagent_type="sp-next", description="sp:next preflight",
      prompt="Identify the next spec-kit phase and return your block. Arguments: $ARGUMENTS")
```

It returns exactly one block. Dispatch on it:

| Block                | Action                                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| `PHASE …`            | Go to Step 2 — claim the task, then invoke the mapped command.                                  |
| `STATUS …`           | Print the agent's status table verbatim and **stop**.                                           |
| `SKIP …`             | Go to Step 3 — close the task with a skip reason.                                               |
| `BLOCKED_FORCE …`    | Show the blockers and ask the user whether to force. If yes, go to Step 2; if no, **stop**.     |
| `IMPLEMENT_SUBTASKS` | Report the ready sub-tasks and suggest `/sp:07-implement` to continue implementation. **Stop**. |
| `BLOCKED …`          | Report: "No ready tasks." Show the blockers and suggest `br dep tree <epic-id>`. **Stop**.      |
| `COMPLETE …`         | Report: "Feature workflow complete! Epic ready to close." **Stop**.                             |
| `NO_EPIC`            | Report: "No active epic found. Run `/sp:02-specify <feature>` to create one." **Stop**.         |
| `ERROR …`            | Surface the reason to the user and **stop**.                                                    |

### Step 2 — Claim and invoke (main session)

a. Claim the phase task **before** invoking, so the claim persists here:

```bash
br update <task-id> --claim
```

b. Display:

```markdown
## /sp:next

**Epic**: [epic-id]
**Next Phase**: [sp:XX-name]
**Task ID**: [task-id]

Invoking `/sp:XX-name`...
```

c. Invoke the mapped command **in this session** via the Skill tool:

| Phase task          | Invocation                       |
| ------------------- | -------------------------------- |
| `[sp:03-plan]`      | `Skill(skill="sp:03-plan")`      |
| `[sp:04-red-team]`  | `Skill(skill="sp:04-red-team")`  |
| `[sp:05-tasks]`     | `Skill(skill="sp:05-tasks")`     |
| `[sp:06-analyze]`   | `Skill(skill="sp:06-analyze")`   |
| `[sp:07-implement]` | `Skill(skill="sp:07-implement")` |
| `[sp:08-harden]`    | `Skill(skill="sp:08-harden")`    |

Use the `command=` value from the agent's `PHASE` block; the table above is the
authority on how to invoke it.

### Step 3 — Skip (main session)

a. Close the reported task:

```bash
br close <task-id> --reason "Skipped by user via /sp:next --skip"
```

b. Report: "Phase [sp:XX-name] skipped."

c. Show what became ready:

```bash
br ready --json | jq '.[] | select(.title | contains("[sp:"))'
```

d. Report the next phase (if any) and suggest re-running `/sp:next`.

## Error Recovery

- **Beads not initialized**: install `br` via the official installer, then run
  `br init`.
- **Circular dependency**: run `br dep cycles` and resolve before continuing.
- **Phase task not found**: list available phases with `br show <epic-id> --json`
  (dependents array).
- **Claim fails**: the task may already be `in_progress` from an interrupted
  run — inspect with `br show <task-id>` before re-invoking.

## Beads Commands Reference

| Action               | Command                                       |
| -------------------- | --------------------------------------------- |
| Claim task           | `br update <id> --claim`                      |
| Close (skip)         | `br close <id> --reason "..."`                |
| Get ready tasks      | `br ready --json`                             |
| View all phases      | `br show <epic-id> --json` (dependents array) |
| View dependency tree | `br dep tree <epic-id> --direction up`        |

## Example Usage

```bash
/sp:next            # progress to the next ready phase
/sp:next --status   # show workflow status without invoking
/sp:next --skip     # skip the current phase
/sp:next 03-plan    # force a specific phase
```
