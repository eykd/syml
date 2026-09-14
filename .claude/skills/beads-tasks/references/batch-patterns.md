# Batch Operation Patterns

Efficient batching patterns for beads commands to minimize tool calls.

## Pattern 1: Bulk Task Creation

### Creating Multiple Independent Tasks

```bash
#!/usr/bin/env bash
set -euo pipefail

br create --title "Implement user authentication" \
  --description "Add JWT-based auth system with login/logout endpoints"

br create --title "Add password hashing" \
  --description "Use bcrypt for secure password storage"

br create --title "Create auth middleware" \
  --description "Middleware to verify JWT tokens on protected routes"

br create --title "Write auth integration tests" \
  --description "Test login, logout, and protected route access"

echo "Created 4 authentication tasks"
```

### Creating Task Hierarchies (Epic + Children)

```bash
#!/usr/bin/env bash
set -euo pipefail

# Create epic first, capture ID with --silent
epic_id=$(br create --title "User Authentication Feature" \
  --description "Complete auth system with JWT, password hashing, and middleware" \
  --type epic --silent)

echo "Created epic: $epic_id"

# Create child tasks under the epic
br create --title "Implement JWT generation" \
  --description "Create token signing and verification functions" \
  --parent "$epic_id"

br create --title "Build login endpoint" \
  --description "POST /api/auth/login with email/password validation" \
  --parent "$epic_id"

br create --title "Build logout endpoint" \
  --description "POST /api/auth/logout to invalidate tokens" \
  --parent "$epic_id"

br create --title "Add auth middleware" \
  --description "Middleware to protect routes requiring authentication" \
  --parent "$epic_id"

echo "Created epic with 4 child tasks"
```

## Pattern 2: Bulk Status Updates

### Claiming Multiple Ready Tasks

```bash
#!/usr/bin/env bash
set -euo pipefail

# Get all ready tasks and claim them
ready_tasks=$(br ready --json | jq -r '.[].id')

for task_id in $ready_tasks; do
  br update "$task_id" --claim
  echo "Claimed: $task_id"
done

echo "Claimed $(echo "$ready_tasks" | wc -l) tasks"
```

### Bulk Close Pattern

```bash
#!/usr/bin/env bash
set -euo pipefail

# Close multiple tasks by ID (br close accepts multiple IDs)
br close task-001 task-002 task-003 task-004 --reason "Sprint cleanup"

echo "Closed 4 tasks"
```

## Pattern 3: Batch Queries and Reporting

### Generate Status Report

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Beads Task Status Report ==="
echo

# Count by status using jq
echo "Task Counts by Status:"
br list --json --limit 0 | jq -r '
  .issues | group_by(.status) |
  map({status: .[0].status, count: length}) |
  .[] |
  "  \(.status): \(.count)"
'

echo
echo "Ready Tasks:"
br ready --json | jq -r '.[] | "  - [\(.id)] \(.title)"'

echo
echo "In Progress Tasks:"
br list --json --status=in_progress | jq -r '.issues[] | "  - [\(.id)] \(.title)"'

echo
echo "Recently Closed (last 5):"
br list --json --all --sort=closed --reverse --limit 5 | jq -r '
  .[] |
  select(.status == "closed") |
  "  - [\(.id)] \(.title)"
'
```

### Filter Tasks by Criteria

```bash
#!/usr/bin/env bash
set -euo pipefail

# Find high-priority open tasks (priority 0 or 1)
echo "High Priority Open Tasks:"
br list --status open --priority-max 1 --json | jq -r '
  .[] | "  [\(.id)] P\(.priority) \(.title)"
'

# Find tasks with specific labels
echo
echo "Tasks Labeled 'security':"
br list --json --label security | jq -r '
  .[] | "  [\(.id)] \(.title)"
'
```

## Pattern 4: Conditional Batch Operations

### Process Tasks Based on State

```bash
#!/usr/bin/env bash
set -euo pipefail

# Claim next task only if nothing currently in progress
in_progress_count=$(br list --json --status=in_progress | jq '.issues | length')

if [ "$in_progress_count" -eq 0 ]; then
  echo "No tasks in progress. Claiming next ready task..."
  next_task=$(br ready --json --limit 1 | jq -r '.[0].id // empty')

  if [ -n "$next_task" ]; then
    br update "$next_task" --claim
    echo "Claimed: $next_task"
  else
    echo "No ready tasks available"
  fi
else
  echo "$in_progress_count task(s) already in progress. Not claiming new tasks."
fi
```

### Batch Create with Validation

```bash
#!/usr/bin/env bash
set -euo pipefail

tasks=(
  "Implement user login|Add JWT-based authentication with email/password"
  "Create user registration|New user signup with email verification"
  "Add password reset|Implement forgot password flow with email tokens"
)

created=0
skipped=0

for task_def in "${tasks[@]}"; do
  IFS='|' read -r title description <<< "$task_def"

  # Check if task with similar title already exists
  existing=$(br list --json --title-contains "$title" | jq -r '.issues[0].id // empty')

  if [ -z "$existing" ]; then
    br create --title "$title" --description "$description"
    echo "Created: $title"
    ((created++))
  else
    echo "Skipped (exists): $title [$existing]"
    ((skipped++))
  fi
done

echo
echo "Summary: Created $created, Skipped $skipped"
```

## Pattern 5: Data Transformation Pipelines

### Extract and Reformat Data

```bash
#!/usr/bin/env bash
set -euo pipefail

# Generate markdown checklist from ready tasks
echo "## Ready Tasks Checklist"
echo
br ready --json | jq -r '.[] | "- [ ] \(.title) (`\(.id)`)"'
```

### Cross-Reference Tasks

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Blocked Tasks ==="

# Use br blocked for blocker-aware results
br blocked --json | jq -r '
  .[] | "Task: \(.title) (\(.id)) - Status: \(.status)"
'
```

## Best Practices

1. **Always use `set -euo pipefail`** at the start of batch scripts to fail fast on errors
2. **Always include `--description`** when creating tasks
3. **Use `--silent`** with `br create` to capture only IDs in scripts
4. **Use `--json`** (not `--format json`) for machine-readable output
5. **Use `br update --claim`** (not `br start`) to claim tasks
6. **Handle edge cases** — check for empty results from jq before processing
7. **Add summary output** — always end batch operations with a count of what was done
8. **Store JSON in variables** — query once, filter multiple times

## When to Use Batch Operations

- **Creating 3+ related tasks** — batch creation instead of individual tool calls
- **Bulk status updates** — moving multiple tasks through workflow states
- **Generating reports** — querying and formatting task data
- **Conditional operations** — complex logic that checks state before acting
- **Data migrations** — one-time operations on many existing tasks
