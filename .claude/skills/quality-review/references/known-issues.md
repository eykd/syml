# Known Issues Handling Reference

Guidance for checking and referencing beads tasks to avoid duplicate issue reporting.

---

## Purpose

GitHub Actions workflows generate `known-issues.json` containing beads tasks already tracked for the feature branch. Quality reviews should reference these tasks rather than re-reporting the same issues.

---

## File Format

`known-issues.json` contains beads tasks in JSON format:

```json
[
  {
    "id": "syml-123",
    "title": "Fix email validation regex",
    "description": "Email validation allows invalid domains",
    "status": "open",
    "priority": "P1",
    "tags": ["bug", "validation"],
    "parent": "syml-100",
    "created": "2024-01-15T10:30:00Z"
  },
  {
    "id": "syml-124",
    "title": "Add tests for edge cases",
    "description": "Missing tests for null/undefined inputs",
    "status": "ready",
    "priority": "P2",
    "tags": ["test", "quality"],
    "parent": "syml-100",
    "created": "2024-01-15T11:00:00Z"
  }
]
```

### Key Fields

- **id**: Unique task identifier (e.g., "syml-123")
- **title**: Short task description
- **description**: Detailed task description
- **status**: Task status ("open", "ready", "done", "cancelled")
- **priority**: Task priority (P1, P2, P3)
- **tags**: Categories for the task
- **parent**: Parent epic ID (the feature branch's epic)

---

## How Known Issues Are Generated

In GitHub Actions workflow (`.github/workflows/claude-code-review.yml`):

```bash
# Extract epic ID from branch name (e.g., feature/syml-123-description)
EPIC_ID=$(echo "$HEAD_REF" | grep -oP 'workspace-\w+' || echo "")

if [ -n "$EPIC_ID" ]; then
  # Query open and ready tasks for this epic
  br show "$EPIC_ID" --json | jq '[.[0].dependents[] | select(.status == "open")]' > known-issues.json
  br ready --json >> known-issues.json
fi
```

**Statuses included**:

- `open`: Work in progress
- `ready`: Ready to be worked on (not started yet)

**Statuses excluded**:

- `done`: Already completed
- `cancelled`: Won't be fixed

---

## Integration in Review Process

### 1. Check for File

Before analyzing PR changes:

```python
# Pseudocode for skill logic
known_issues = []
if file_exists("known-issues.json"):
    known_issues = json.loads(read_file("known-issues.json"))
```

**If file doesn't exist**: Skip known issues check, report all findings normally.

### 2. Parse Tasks

Extract relevant information from known issues:

```python
# Pseudocode
tracked_issues = [
    {"id": t["id"], "title": t["title"], "description": t["description"], "tags": t["tags"]}
    for t in known_issues
    if t["status"] in ("open", "ready")
]
```

### 3. Match Findings

When generating a finding, check if it relates to a known issue:

```python
# Pseudocode
def check_known_issue(finding, known_issues):
    for issue in known_issues:
        if (
            issue["title"] in finding["file"]
            or issue["description"] in finding["description"]
            or any(tag in issue["tags"] for tag in finding["tags"])
        ):
            return issue["id"]
    return None
```

**Matching criteria** (any of these):

- Finding relates to the same file/function mentioned in task title
- Finding description overlaps with task description
- Finding addresses the same problem area

### 4. Reference Known Issues

When a finding matches a known issue:

**Option A: Reference and skip**

```markdown
<!-- Don't report as new finding -->

Note: Email validation issue in src/syml/parsers.py:45 is tracked in beads task syml-123
```

**Option B: Reference and enhance**

```markdown
### Finding: Email validation allows invalid domains

- **Related to beads task**: syml-123
- **File**: src/syml/parsers.py:45
- **Additional context**: Also affects src/syml/nodes.py:67 (not in original task)
- **Fix**: See beads task for detailed fix plan
```

Use Option A if finding is identical to known issue.
Use Option B if finding adds new information.

### 5. Report Only New Findings

Only create new findings for issues that:

- Don't match any known issue
- Add significant new information to a known issue
- Affect different files/areas than the known issue

---

## Reference Format

When referencing a known issue in review output:

### In Finding Description

```markdown
### Finding: Missing error handling

- **Related to beads task**: syml-125
- **File**: src/syml/basetypes.py:30
- **Description**: No error handling for network failures
- **Impact**: [same as normal finding]
- **Fix**: See beads task syml-125 for implementation plan
```

### In Summary Section

```markdown
## Summary

This PR addresses several quality concerns:

**Known Issues (from beads)**:

- syml-123: Email validation (in progress)
- syml-124: Edge case tests (ready to work)

**New Findings**:

- Must Fix: 2 new issues
- Should Fix: 3 quality improvements
- Consider: 1 suggestion
```

---

## Edge Cases

### No known-issues.json File

**Scenario**: File doesn't exist (not in GitHub Actions, or branch has no epic)

**Action**: Skip known issues check entirely, report all findings normally

**Code**:

```python
if not file_exists("known-issues.json"):
    # Report all findings without filtering
    return findings
```

### Empty known-issues.json

**Scenario**: File exists but contains empty array `[]`

**Action**: Same as no file - report all findings

**Code**:

```python
known_issues = json.loads(read_file("known-issues.json"))
if len(known_issues) == 0:
    # Report all findings without filtering
    return findings
```

### Malformed JSON

**Scenario**: File exists but contains invalid JSON

**Action**: Log warning, skip known issues check, report all findings

**Code**:

```python
try:
    known_issues = json.loads(read_file("known-issues.json"))
except json.JSONDecodeError:
    logger.warning("Failed to parse known-issues.json, reporting all findings")
    return findings
```

### All Findings Match Known Issues

**Scenario**: Every finding relates to an existing beads task

**Action**: Acknowledge all tasks referenced, no new findings section

**Output**:

```markdown
## Code Quality Review

All quality concerns found in this PR are already tracked in beads:

- syml-123: Email validation (in progress)
- syml-124: Edge case tests (ready)
- syml-125: Error handling (ready)

No new quality issues detected.
```

---

## Benefits of Known Issues Integration

1. **Reduces noise**: Don't re-report issues already being tracked
2. **Maintains context**: Connect review findings to project task tracking
3. **Shows progress**: Distinguish new issues from work-in-progress
4. **Improves workflow**: Reviewers see what's new vs already known
5. **Enables tracking**: Beads tasks provide detailed fix plans and status

---

## Example Review with Known Issues

```markdown
## Code Quality Review

### What Changed

Added user registration endpoint with email validation.

### Known Issues Status

The following issues are already tracked in beads:

- **syml-123** (in progress): Email validation regex needs improvement
- **syml-124** (ready): Missing tests for null email input

### Does It Work

✅ Core registration logic works correctly
✅ Password hashing implemented properly
⚠️ Email validation improvements tracked in syml-123

### Test Quality

❌ Missing edge case tests (tracked in syml-124)
✅ Happy path tests are well-written
✅ 100% coverage for new code

### Findings

#### Must Fix

None - all issues are tracked in beads or have been addressed.

#### Should Fix

1. **Extract validation to utility** - src/syml/parsers.py:45
   - **Problem**: Email validation duplicated in register and login
   - **Impact**: Maintenance burden
   - **Fix**: Extract to shared validateEmail() utility

## Summary

This PR makes good progress on user registration. The two main quality concerns (email validation and edge case tests) are already tracked in beads tasks syml-123 and syml-124.

One new "Should Fix" item identified: extract validation logic to avoid duplication.
```

---

## Quick Reference

**Check for file**: `fileExists('known-issues.json')`
**Parse safely**: Wrap in try-catch
**Filter statuses**: Include "open" and "ready" only
**Match findings**: Compare file, description, tags
**Reference format**: `Related to beads task syml-123`
**Report new only**: Skip if identical to known issue
