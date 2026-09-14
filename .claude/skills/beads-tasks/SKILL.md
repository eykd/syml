---
name: beads-tasks
description: 'Create, query, update, and close beads tasks with br. Use when managing the beads task queue: creating tasks or epics, claiming/closing tasks, adding dependencies, or querying ready work — and to avoid common br CLI flag mistakes.'
---

# Beads Task Management

Workflow guide for creating, querying, updating, and closing beads tasks with `br`.

## Gotchas — Read First

| Trap                  | Wrong                                | Correct                                                                                              |
| --------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| JSON output flag      | `--format json`                      | `--json` (global flag, before or after subcommand)                                                   |
| Start/claim a task    | `br start <id>`                      | `br update <id> --claim` (atomic assign + in_progress)                                               |
| Priority values       | `"high"`, `"medium"`, `"low"`        | `0-4` or `P0-P4` (integers, 0 = highest; default 2)                                                  |
| JSON field names      | camelCase (`createdAt`, `blockedBy`) | snake_case (`created_at`, `dependency_count`)                                                        |
| Issue type field      | `type`                               | `issue_type` in JSON output                                                                          |
| Ready vs list --ready | `br list --ready` = `br ready`       | **NOT equivalent** — `br ready` uses blocker-aware semantics; `br list` has no `--ready` flag at all |
| List children         | `br list --parent <id>`              | `br show <id> --json` then parse `.[0].dependents[]`; `br list` has no `--parent` flag               |
| Children subcommand   | `br children <id>`                   | Does not exist; use `br show <id> --json` and parse `.[0].dependents[]`                              |
| Query expressions     | `br query "status=open AND ..."`     | `br query` now manages saved queries only (save/run/list/delete); use `br list` flags to filter      |
| Close reason          | `--close-reason`                     | `br close <id> --reason "..."`                                                                       |
| Sync import           | `br sync --import`                   | `br sync --import-only` (full flag name required)                                                    |
| DB corruption         | Retry / blind `br doctor --repair`   | Needs `br >= 0.5.5` — older builds silently drop data (beads_rust#457); see "DB corruption" below    |
| List JSON output      | `br list --json` = bare array        | Returns `{"issues": [...], "total": N, ...}`; access items via `.issues[]` in jq                     |
| Dep tree direction    | `br dep tree <id>` shows children    | Default `--direction down` shows blockers; use `--direction up` to see children/dependents           |

### DB corruption

Every `br` build before 0.5.5 has a cross-process WAL checkpoint race in its
embedded FrankenSQLite engine (beads_rust#457). Under concurrent use it silently
dropped issues and dependency edges and left `br doctor` reporting
`integrity_check: page N is never used`. Retrying, or running
`br doctor --repair` twice, hid the symptom without fixing anything. Fixed
engine-side in 0.5.5.

- First check `br --version` is `>= 0.5.5`; if not, run `/install-br`.
- On a current build, run `br doctor --repair` once. If it refuses because a
  prior recovery already failed, rerun with `--allow-repeated-repair`.
- If `br doctor` still reports `integrity_check` or `SCHEMA_MISMATCH`, rebuild
  from the committed JSONL (the source of truth):
  `rm -f .beads/beads.db .beads/beads.db-wal .beads/beads.db-shm && br sync --import-only --rebuild`

## Task Parenting (ralph automation)

Ad-hoc tasks created during planning, reviews, or mid-implementation **must** be parented to the current branch's `[sp:07-implement]` task — otherwise ralph's leaf-finder ignores them.

**Branch-aware pattern (preferred):**

```bash
# 1. Derive feature name from current branch (strip leading digits)
feature=$(git branch --show-current | sed 's/^[0-9]*-//')

# 2. Find the epic whose title contains the feature name
#    (ralph uses: ascii_downcase, hyphens→spaces, substring match)
epic_id=$(br list --type epic --status open --json | \
  jq -r --arg f "$feature" \
  '.issues[] | select(.title | ascii_downcase | gsub("-";" ") | contains($f | ascii_downcase | gsub("-";" "))) | .id' | head -n1)

# 3. Find the [sp:07-implement] child of that epic
implement_id=$(br show "$epic_id" --json | \
  jq -r '.[0].dependents[] | select(.title | contains("[sp:07-implement]")) | .id')

# 4. Create with parent
br create --title "Fix edge case in auth" \
  --description "Handle expired tokens gracefully" \
  --parent "$implement_id" --priority 1

# 5. (Optional) Add dependency
br dep add <new-task> <prerequisite>
```

**Filing blockers on the task you're currently working on:**

If you discover problems during implementation that must be fixed before you
can finish the current task, file the new tasks as blockers **and revert your
own task to `open`** so ralph can re-surface it once the blockers clear:

```bash
# File a blocker and link it
blocker_id=$(br create --title "Fix broken assumption X" \
  --description "Discovered during <current task>; must land first" \
  --parent "$impl_id" --priority 1 --silent)
br dep add <current-task-id> "$blocker_id"

# Revert yourself so `br ready` can pick you up again after blockers close
br update <current-task-id> --status open
```

Ralph has a safety net that reverts in_progress tasks with new blockers, but
setting status explicitly is clearer and leaves an audit trail.

**Filing bugs during testing:**

```bash
feature=$(git branch --show-current | sed 's/^[0-9]*-//')
epic_id=$(br list --type epic --status open --json | \
  jq -r --arg f "$feature" \
  '.issues[] | select(.title | ascii_downcase | gsub("-";" ") | contains($f | ascii_downcase | gsub("-";" "))) | .id' | head -n1)
impl_id=$(br show "$epic_id" --json | \
  jq -r '.[0].dependents[] | select(.title | contains("[sp:07-implement]")) | .id')
br create --title "Bug: describe the issue" \
  --description "Steps to reproduce and expected behavior" \
  --parent "$impl_id" --priority 1 --add-label "bug"
```

If no matching epic exists, create the task normally and consider starting one with `/sp:02-specify`.

## Quick Command Reference

| Action          | Command                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------ |
| Create task     | `br create --title "..." --description "..." [--parent ID] [--priority 0-4] [--type task]` |
| Create (script) | `br create --title "..." --description "..." --silent` (outputs only ID)                   |
| List open       | `br list` (default: open, limit 50)                                                        |
| List filtered   | `br list --status=in_progress --type=task --assignee=me`                                   |
| Show ready work | `br ready` (blocker-aware, not same as `list --ready`)                                     |
| Show details    | `br show <id> [--json]`                                                                    |
| Show children   | `br show <id> --json \| jq '.[0].dependents[]'`                                            |
| Text search     | `br search "keyword" [--status open] [--limit 20]`                                         |
| Claim task      | `br update <id> --claim`                                                                   |
| Update fields   | `br update <id> --status open --priority 1 --add-label "bug"`                              |
| Close           | `br close <id> [--reason "..."] [--suggest-next]`                                          |
| Close multiple  | `br close id1 id2 id3`                                                                     |
| Add dependency  | `br dep add <blocked> <blocker>`                                                           |
| Dep tree        | `br dep tree <id> [--direction=up\|down\|both]` (default: down=blockers, up=children)      |
| Epic status     | `br epic status [--eligible-only]`                                                         |
| Children        | `br show <parent-id> --json \| jq '.[0].dependents[]'`                                     |
| Blocked         | `br blocked`                                                                               |
| Count           | `br count [--status=open] [--type=task]`                                                   |

## Batch Operations

**Core principle: one script, many operations.** Create a single Bash script that executes multiple `br` commands rather than making separate tool calls.

### Batch create with parent

```bash
#!/usr/bin/env bash
set -euo pipefail

parent_id="$1"  # e.g., the [sp:07-implement] task ID

for task in \
  "Implement auth|Add JWT-based auth with login/logout" \
  "Add password hashing|Use bcrypt for secure password storage" \
  "Create auth middleware|Verify JWT tokens on protected routes" \
; do
  IFS='|' read -r title desc <<< "$task"
  id=$(br create --title "$title" --description "$desc" \
    --parent "$parent_id" --priority 2 --silent)
  echo "Created: $id - $title"
done
```

### Claim and work on next ready task

```bash
next=$(br ready --json --limit 1 | jq -r '.[0].id // empty')
if [ -n "$next" ]; then
  br update "$next" --claim
  echo "Claimed: $next"
fi
```

### Bulk close completed tasks

```bash
br close task-1 task-2 task-3 --reason "Sprint cleanup"
```

### Status report

```bash
tasks=$(br list --json --limit 0)
echo "$tasks" | jq -r '
  .issues | group_by(.status) |
  map({status: .[0].status, count: length}) |
  .[] | "  \(.status): \(.count)"
'
```

## JSON Output + jq

Always use the `--json` global flag (not `--format json`):

```bash
br list --json                    # {"issues": [...], "total": N, "limit": N, "offset": N, "has_more": bool}
br show <id> --json               # Bare array with single object (+ dependents)
br ready --json                   # Bare array of ready tasks
br blocked --json                 # Bare array of blocked tasks
br create --title "..." --json    # Created task object
```

**Important**: `br list --json` wraps results in `{"issues": [...]}` (paginated). Other commands (`br show`, `br ready`, `br blocked`, `br search`) return bare arrays. Access items from `br list` via `.issues[]`, not `.[]`.

**Actual field names** (snake_case, from live CLI output):

```
id, title, description, status, priority (int), issue_type,
owner, assignee, created_at, created_by, updated_at,
closed_at, close_reason, dependency_count, dependent_count,
comment_count, parent_id, labels, metadata
```

### Common jq patterns

```bash
# Extract IDs (note: br list wraps in .issues, other commands return bare arrays)
br list --json | jq -r '.issues[].id'

# Filter by status
br list --json | jq '.issues[] | select(.status == "in_progress")'

# Count by status
br list --json | jq '.issues | group_by(.status) | map({s: .[0].status, n: length}) | .[]'

# Sort by priority (0 = highest)
br list --json | jq '.issues | sort_by(.priority)'

# Markdown checklist (br ready returns bare array)
br ready --json | jq -r '.[] | "- [ ] \(.title) (`\(.id)`)"'

# Get children of a parent
br show <parent-id> --json | jq -r '.[0].dependents[] | "\(.id): \(.title) [\(.status)]"'
```

## Best Practices

1. **Always include `--description`** when creating tasks — descriptions explain purpose, not just repeat titles
2. **Use `--silent`** in scripts to capture only the ID from `br create`
3. **Use `set -euo pipefail`** in batch scripts to fail fast
4. **Parent to `[sp:07-implement]`** for ad-hoc tasks during active epics
5. **Use `br ready`** (not `br list --ready`) to find truly claimable work
6. **Use `br update --claim`** (not `br start`) to atomically claim a task
7. **Store JSON in a variable** if processing it multiple times to avoid redundant queries
8. **Use `--limit 0`** with `br list` for unlimited results (default is 50)

## References

| File                                                | Contents                                                      |
| --------------------------------------------------- | ------------------------------------------------------------- |
| [cli-reference.md](./references/cli-reference.md)   | Complete command reference from actual `--help` output        |
| [batch-patterns.md](./references/batch-patterns.md) | Detailed batch scripting patterns with 5 recipes              |
| [jq-cookbook.md](./references/jq-cookbook.md)       | jq extraction, filtering, aggregation, and debugging patterns |
