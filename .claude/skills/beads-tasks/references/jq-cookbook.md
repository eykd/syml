# jq Cookbook for Beads

Practical jq patterns for processing beads JSON output in batch operations.

## Prerequisites

All beads commands support `--json` (global flag) for machine-readable output:

```bash
br list --json
br ready --json
br show <id> --json
```

**Pitfall:** The flag is `--json`, NOT `--format json`. The `--format` flag is for Go template formatting, not JSON output.

## Basic Extraction Patterns

### Get All Task IDs

```bash
br list --json | jq -r '.issues[].id'
```

### Get Task Titles and IDs

```bash
br list --json | jq -r '.issues[] | "\(.id): \(.title)"'
```

### Extract Specific Fields

```bash
# Just titles
br list --json | jq -r '.issues[].title'

# Title, status, and priority
br list --json | jq -r '.issues[] | "\(.title) | \(.status) | P\(.priority)"'
```

## Filtering Patterns

### Filter by Status

```bash
# All open tasks
br list --json | jq '.issues[] | select(.status == "open")'

# All closed tasks (need --all to include closed in list output)
br list --json --all | jq '.issues[] | select(.status == "closed")'

# In-progress tasks
br list --json | jq '.issues[] | select(.status == "in_progress")'
```

### Filter by Multiple Conditions

```bash
# High priority tasks that are open (priority 0 or 1)
br list --json | jq '.issues[] | select(.priority <= 1 and .status == "open")'

# Open tasks of a specific type
br list --json | jq '.issues[] | select(.status == "open" and .issue_type == "task")'

# Tasks with no dependencies
br list --json | jq '.issues[] | select(.dependency_count == 0)'
```

### Filter by Label Presence

```bash
# Tasks with a specific label (use br list --label flag instead when possible)
br list --json --label "bug" | jq -r '.issues[] | .id'

# Tasks with any labels
br list --json | jq '.issues[] | select(.labels != null and (.labels | length > 0))'

# Tasks without labels
br list --json | jq '.issues[] | select(.labels == null or (.labels | length == 0))'
```

## Aggregation Patterns

### Count by Status

```bash
br list --json --limit 0 | jq -r '
  .issues | group_by(.status) |
  map({status: .[0].status, count: length}) |
  .[] |
  "\(.status): \(.count)"
'
```

### Count by Priority

```bash
br list --json --limit 0 | jq -r '
  .issues | group_by(.priority) |
  map({priority: .[0].priority, count: length}) |
  .[] |
  "P\(.priority): \(.count)"
'
```

### Count by Issue Type

```bash
br list --json --limit 0 | jq -r '
  .issues | group_by(.issue_type) |
  map({type: .[0].issue_type, count: length}) |
  .[] |
  "\(.type): \(.count)"
'
```

## Sorting Patterns

### Sort by Created Date (Newest First)

```bash
br list --json | jq '.issues | sort_by(.created_at) | reverse | .[]'
```

### Sort by Priority (Highest First, 0 = Highest)

```bash
br list --json | jq '.issues | sort_by(.priority) | .[]'
```

### Sort by Title (Alphabetical)

```bash
br list --json | jq '.issues | sort_by(.title) | .[]'
```

## Transformation Patterns

### Convert to Markdown Checklist

```bash
br ready --json | jq -r '.[] | "- [ ] \(.title) (`\(.id)`)"'
```

### Generate CSV Output

```bash
# Header
echo "ID,Title,Status,Priority"

# Data rows
br list --json | jq -r '
  .issues[] |
  [.id, .title, .status, .priority] |
  @csv
'
```

### Create JSON Summary Object

```bash
br list --json --limit 0 | jq '.issues | {
  total: length,
  by_status: (group_by(.status) | map({(.[0].status): length}) | add),
  open_count: ([.[] | select(.status == "open")] | length),
  in_progress_count: ([.[] | select(.status == "in_progress")] | length)
}'
```

## Complex Queries

### Find Tasks by Epic (Children)

```bash
# List children of a specific parent via br show
br show <epic-id> --json | jq -r '.[0].dependents[] | "\(.id): \(.title) [\(.status)]"'
```

### Find Blocked Tasks with Details

```bash
br blocked --json | jq -r '
  .[] | "\(.id): \(.title) (status: \(.status))"
'
```

## Conditional Logic in jq

### Use Alternative Values

```bash
# Use "none" if assignee is null
br list --json | jq -r '.issues[] | .assignee // "unassigned"'

# Default for missing fields
br list --json | jq '.issues[] | .labels // []'
```

### Conditional Field Selection

```bash
# Show different output based on status
br list --json | jq -r '
  .issues[] |
  if .status == "closed" then
    "DONE \(.title)"
  elif .status == "in_progress" then
    "WIP  \(.title)"
  else
    "TODO \(.title)"
  end
'
```

## Integration with Bash

### Store IDs in Array

```bash
# Store ready task IDs in Bash array
mapfile -t ready_ids < <(br ready --json | jq -r '.[].id')

# Iterate over array
for id in "${ready_ids[@]}"; do
  echo "Processing: $id"
  br update "$id" --claim
done
```

### Conditional Execution Based on Query

```bash
# Check if any tasks are in progress
in_progress=$(br list --json --status=in_progress | jq '.issues | length')

if [ "$in_progress" -gt 0 ]; then
  echo "Tasks in progress: $in_progress"
else
  echo "No tasks in progress"
fi
```

### Capture Single Value

```bash
# Get the first ready task ID
next_task=$(br ready --json --limit 1 | jq -r '.[0].id // empty')

if [ -n "$next_task" ]; then
  echo "Claiming task: $next_task"
  br update "$next_task" --claim
else
  echo "No ready tasks"
fi
```

## Debugging jq Queries

### Pretty Print JSON

```bash
br list --json | jq '.'
```

### View Array Length

```bash
br list --json | jq '.issues | length'
```

### Inspect First Item (see actual field names)

```bash
br list --json | jq '.issues[0]'
```

### Test Filter Without Processing

```bash
# See how many would be selected
br list --json | jq '[.issues[] | select(.status == "open")] | length'
```

## Common Pitfalls

### Pitfall: Using `--format json` instead of `--json`

**Problem:** `--format` is for Go template output, not JSON.

**Solution:** Always use `--json` (a global flag):

```bash
# Wrong
br list --format json

# Correct
br list --json
```

### Pitfall: "Cannot index null"

**Problem:** Trying to access a field that doesn't exist on some objects.

**Solution:** Use the optional operator `?` or null coalescing `//`:

```bash
# Bad
jq '.[] | .assignee'

# Good
jq '.[] | .assignee // "none"'
jq '.[] | .assignee?'
```

### Pitfall: Empty Output

**Problem:** Filter is too restrictive or field names are wrong.

**Solution:** Test incrementally and verify field names:

```bash
# Step 1: See all tasks
br list --json | jq '.'

# Step 2: See first task structure (verify field names)
br list --json | jq '.issues[0]'

# Step 3: Test filter
br list --json | jq '.issues[] | select(.status == "open")'
```

Remember: fields are **snake_case** (`created_at`, `issue_type`, `dependency_count`), NOT camelCase.

### Pitfall: Using string priority values

**Problem:** Priority is an integer (0-4), not a string.

```bash
# Wrong
jq '.[] | select(.priority == "high")'

# Correct
jq '.[] | select(.priority <= 1)'  # P0 and P1 (highest)
```

### Pitfall: Unexpected Type Errors

**Problem:** Trying to use string operators on arrays or vice versa.

**Solution:** Check types:

```bash
# See type of a field
br list --json | jq '.issues[0].labels | type'

# Handle arrays vs strings
br list --json | jq '.issues[] | .labels[]?'  # Iterate array safely
```

## Performance Tips

1. **Use br's own filters first** — `--status`, `--type`, `--label` filter at the source, reducing JSON size
2. **Filter early in jq** — use `select()` before `sort_by()` or other operations
3. **Limit output** — use `.[0:10]` to take first 10 items if you don't need all
4. **Avoid repeated queries** — store JSON in a variable if you'll process it multiple times

```bash
# Good: Query once
tasks=$(br list --json --limit 0)
echo "$tasks" | jq '.issues | filter expression 1'
echo "$tasks" | jq '.issues | filter expression 2'

# Bad: Query multiple times
br list --json | jq '.issues | filter expression 1'
br list --json | jq '.issues | filter expression 2'
```

## Reference

- [jq Manual](https://jqlang.github.io/jq/manual/)
- [jq Playground](https://jqplay.org/) — test queries online
- CLI reference: see `references/cli-reference.md`
