# br CLI Reference

Authoritative command reference derived from actual `br <cmd> --help` output. When in doubt, run `br <cmd> --help` to verify.

## Installation

```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh" | bash
```

## Global Flags

These flags work with every `br` command:

| Flag             | Description                                                               |
| ---------------- | ------------------------------------------------------------------------- |
| `--json`         | Output in JSON format                                                     |
| `--actor <name>` | Actor name for audit trail (default: `$BR_ACTOR`, git user.name, `$USER`) |
| `--db <path>`    | Database path (default: auto-discover `.beads/*.db`)                      |
| `-q, --quiet`    | Suppress non-essential output (errors only)                               |
| `-v, --verbose`  | Enable verbose/debug output                                               |
| `--readonly`     | Read-only mode: block write operations                                    |
| `--sandbox`      | Sandbox mode: disables auto-sync                                          |
| `--allow-stale`  | Allow operations on potentially stale data                                |

## br create

Create a new issue (or multiple issues from markdown file).

```
br create [title] [flags]
```

**Aliases:** `create`, `new`

### Key Flags

| Flag                         | Description                                                               |
| ---------------------------- | ------------------------------------------------------------------------- |
| `--title <string>`           | Issue title (alternative to positional argument)                          |
| `-d, --description <string>` | Issue description                                                         |
| `--body-file <path>`         | Read description from file (use `-` for stdin)                            |
| `-t, --type <string>`        | Issue type: `bug\|feature\|task\|epic\|chore\|decision` (default: `task`) |
| `-p, --priority <string>`    | Priority `0-4` or `P0-P4`, 0=highest (default: `2`)                       |
| `--parent <id>`              | Parent issue ID for hierarchical child                                    |
| `-a, --assignee <string>`    | Assignee                                                                  |
| `-l, --labels <strings>`     | Labels (comma-separated)                                                  |
| `-e, --estimate <int>`       | Time estimate in minutes                                                  |
| `--due <string>`             | Due date/time (`+6h`, `+1d`, `tomorrow`, `2025-01-15`)                    |
| `--defer <string>`           | Defer until date (hidden from `br ready` until then)                      |
| `--deps <strings>`           | Dependencies in format `type:id` or `id`                                  |
| `--notes <string>`           | Additional notes                                                          |
| `--acceptance <string>`      | Acceptance criteria                                                       |
| `--design <string>`          | Design notes                                                              |
| `--spec-id <string>`         | Link to specification document                                            |
| `--external-ref <string>`    | External reference (e.g., `gh-9`, `jira-ABC`)                             |
| `--metadata <string>`        | Custom metadata (JSON string or `@file.json`)                             |
| `--silent`                   | Output only the issue ID (for scripting)                                  |
| `--dry-run`                  | Preview without creating                                                  |
| `-f, --file <path>`          | Create multiple issues from markdown file                                 |
| `--no-inherit-labels`        | Don't inherit labels from parent                                          |
| `--ephemeral`                | Create as ephemeral (subject to TTL compaction)                           |

## br list

List issues. Default: open issues, limit 50.

```
br list [flags]
```

### Key Flags

| Flag                          | Description                                                              |
| ----------------------------- | ------------------------------------------------------------------------ |
| `-s, --status <string>`       | Filter by status: `open`, `in_progress`, `blocked`, `deferred`, `closed` |
| `-t, --type <string>`         | Filter by type (can be repeated)                                         |
| `-p, --priority <string>`     | Filter by priority (`0-4` or `P0-P4`, can be repeated)                   |
| `--priority-min/max <string>` | Priority range (inclusive)                                               |
| `--assignee <string>`         | Filter by assignee                                                       |
| `--unassigned`                | Filter for unassigned issues only                                        |
| `-l, --label <strings>`       | Filter by labels (AND logic, can be repeated)                            |
| `--label-any <strings>`       | Filter by labels (OR logic, can be repeated)                             |
| `-n, --limit <int>`           | Limit results (default 50, use 0 for unlimited)                          |
| `--offset <int>`              | Number of results to skip (for pagination, default 0)                    |
| `--sort <field>`              | Sort by: `priority`, `created_at`, `updated_at`, `title`                 |
| `-r, --reverse`               | Reverse sort order                                                       |
| `-a, --all`                   | Include closed issues                                                    |
| `--overdue`                   | Issues with `due_at` in the past                                         |
| `--deferred`                  | Include deferred issues                                                  |
| `--title-contains <string>`   | Filter by title substring (case-insensitive)                             |
| `--desc-contains <string>`    | Filter by description substring                                          |
| `--notes-contains <string>`   | Filter by notes substring                                                |
| `--pretty`                    | Use tree/pretty output format                                            |
| `--long`                      | Detailed multi-line output                                               |
| `--id <string>`               | Filter by specific IDs (can be repeated)                                 |

**Note**: `br list` does NOT support `--parent`, `--no-parent`, or `--ready` flags. To list children, use `br show <parent-id> --json` and parse `.[0].dependents[]`. For ready work, use `br ready`.

**JSON output**: `br list --json` returns `{"issues": [...], "total": N, "limit": N, "offset": N, "has_more": bool}` (paginated envelope), NOT a bare array. Use `.issues[]` in jq, not `.[]`.

## br show

Show issue details.

```
br show [id...] [--id=<id>...] [flags]
```

**Aliases:** `show`, `view`

| Flag                | Description                                          |
| ------------------- | ---------------------------------------------------- |
| `--format <FORMAT>` | Output format: `text` (default), `json`, `toon`      |
| `--wrap`            | Wrap long lines instead of truncating in text output |
| `--stats`           | Show token savings stats when using TOON output      |

**Note**: `br show` does NOT support `--children`, `--refs`, `--short`, `--local-time`, or `--watch` flags.

**JSON output note:** `br show <id> --json` returns an array. For a single issue, the object is at `.[0]`. When the issue has children, they appear in the `dependents` array within the object.

## br ready

Show ready work — open issues with no active blockers.

```
br ready [flags]
```

**Important:** `br ready` is the only way to get blocker-aware ready work. `br list` does NOT have a `--ready` flag — filtering by `--status open` alone misses dependency-blocked issues. Always use `br ready` for task selection.

| Flag                      | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `-n, --limit <int>`       | Maximum issues (default 10)                    |
| `-p, --priority <int>`    | Filter by priority                             |
| `-t, --type <string>`     | Filter by type                                 |
| `-a, --assignee <string>` | Filter by assignee                             |
| `-u, --unassigned`        | Only unassigned issues                         |
| `-l, --label <strings>`   | Filter by labels (AND)                         |
| `--label-any <strings>`   | Filter by labels (OR)                          |
| `--parent <id>`           | Filter to descendants of this bead/epic        |
| `-s, --sort <string>`     | Sort: `priority` (default), `hybrid`, `oldest` |
| `--plain`                 | Plain numbered list (no tree)                  |
| `--pretty`                | Tree format (default true)                     |
| `--include-deferred`      | Include future deferred issues                 |
| `--include-ephemeral`     | Include wisps                                  |
| `--gated`                 | Find molecules ready for gate-resume dispatch  |
| `--mol <id>`              | Filter to steps within a molecule              |

## br update

Update one or more issues. If no ID given, updates last touched issue.

```
br update [id...] [flags]
```

| Flag                         | Description                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------ |
| `--claim`                    | Atomically claim (sets assignee to you, status to `in_progress`; fails if already claimed) |
| `-s, --status <string>`      | New status                                                                                 |
| `--title <string>`           | New title                                                                                  |
| `-d, --description <string>` | New description                                                                            |
| `-p, --priority <string>`    | Priority (`0-4` or `P0-P4`)                                                                |
| `-t, --type <string>`        | New type                                                                                   |
| `-a, --assignee <string>`    | Assignee                                                                                   |
| `--parent <id>`              | Reparent (empty string to remove parent)                                                   |
| `--add-label <strings>`      | Add labels                                                                                 |
| `--remove-label <strings>`   | Remove labels                                                                              |
| `--set-labels <strings>`     | Replace all labels                                                                         |
| `--notes <string>`           | Additional notes                                                                           |
| `--append-notes <string>`    | Append to notes                                                                            |
| `-e, --estimate <int>`       | Time estimate in minutes                                                                   |
| `--due <string>`             | Due date (empty to clear)                                                                  |
| `--defer <string>`           | Defer until date (empty to clear)                                                          |
| `--acceptance <string>`      | Acceptance criteria                                                                        |
| `--design <string>`          | Design notes                                                                               |
| `--spec-id <string>`         | Link to spec                                                                               |
| `--external-ref <string>`    | External reference                                                                         |
| `--metadata <string>`        | Set metadata (JSON or `@file.json`)                                                        |
| `--set-metadata <key=value>` | Set metadata key (repeatable)                                                              |
| `--unset-metadata <key>`     | Remove metadata key (repeatable)                                                           |
| `--body-file <path>`         | Read description from file                                                                 |

## br close

Close one or more issues. If no ID given, closes last touched issue.

```
br close [id...] [flags]
```

| Flag                    | Description                                       |
| ----------------------- | ------------------------------------------------- |
| `-r, --reason <string>` | Reason for closing                                |
| `--suggest-next`        | Show newly unblocked issues after closing         |
| `--continue`            | Auto-advance to next molecule step                |
| `--no-auto`             | With `--continue`, show next step but don't claim |
| `-f, --force`           | Force close pinned issues or unsatisfied gates    |

## br query

**Changed**: `br query` now manages saved queries only. It no longer accepts inline query expressions.

```
br query <COMMAND>
```

### Subcommands

| Command  | Description                              |
| -------- | ---------------------------------------- |
| `save`   | Save current filter set as a named query |
| `run`    | Run a saved query                        |
| `list`   | List all saved queries                   |
| `delete` | Delete a saved query                     |

**To filter issues**, use `br list` flags (`--status`, `--type`, `--priority`, `--title-contains`, etc.) instead of inline query expressions.

## br search

Search issues by text across title, description, and ID.

```
br search [query] [flags]
```

| Flag                            | Description            |
| ------------------------------- | ---------------------- |
| `-s, --status <string>`         | Filter by status       |
| `-t, --type <string>`           | Filter by type         |
| `-a, --assignee <string>`       | Filter by assignee     |
| `-l, --label <strings>`         | Filter by labels (AND) |
| `--label-any <strings>`         | Filter by labels (OR)  |
| `-n, --limit <int>`             | Limit (default 50)     |
| `--sort <field>`                | Sort by field          |
| `-r, --reverse`                 | Reverse sort           |
| `--long`                        | Detailed output        |
| `--priority-min/max <string>`   | Priority range         |
| `--created-after/before <date>` | Date range             |
| `--updated-after/before <date>` | Date range             |
| `--desc-contains <string>`      | Description substring  |
| `--no-assignee`                 | No assignee            |
| `--no-labels`                   | No labels              |

## br dep

Manage dependencies between issues.

### Subcommands

**`br dep add <blocked> <blocker>`** — Add a dependency (blocked depends on blocker).

```bash
br dep add syml-42 syml-41             # syml-42 depends on syml-41
br dep add syml-42 --blocked-by syml-41  # Same (flag syntax)
br dep syml-41 --blocks syml-42        # Same (reverse syntax)
```

Types: `blocks` (default), `tracks`, `related`, `parent-child`, `discovered-from`, `until`, `caused-by`, `validates`, `relates-to`, `supersedes`

**`br dep remove <blocked> <blocker>`** — Remove a dependency.

**`br dep list <id>`** — List dependencies or dependents.

| Flag                     | Description                                        |
| ------------------------ | -------------------------------------------------- |
| `--direction <down\|up>` | `down` = dependencies (default), `up` = dependents |
| `-t, --type <string>`    | Filter by dependency type                          |

**`br dep tree <id>`** — Show dependency tree.

| Flag                           | Description                 |
| ------------------------------ | --------------------------- |
| `--direction <down\|up\|both>` | Tree direction              |
| `-d, --max-depth <int>`        | Max depth (default 50)      |
| `--status <string>`            | Filter by status            |
| `-t, --type <string>`          | Filter by dependency type   |
| `--format mermaid`             | Output as Mermaid flowchart |

**`br dep cycles`** — Detect dependency cycles.

**`br dep relate <id1> <id2>`** — Create bidirectional relates_to link.

## br epic

Epic management commands.

**`br epic status`** — Show epic completion status.

| Flag              | Description                          |
| ----------------- | ------------------------------------ |
| `--eligible-only` | Show only epics eligible for closure |

**`br epic close-eligible`** — Close epics where all children are complete.

| Flag        | Description             |
| ----------- | ----------------------- |
| `--dry-run` | Preview without closing |

## br children (DOES NOT EXIST)

**This subcommand does not exist in br.** To list children, use:

```bash
# Get children via br show (includes dependents array in JSON output)
br show <parent-id> --json | jq '.[0].dependents[]'

# Or view hierarchy via dep tree (--direction up shows children/dependents)
br dep tree <parent-id> --direction up
```

## br blocked

Show blocked issues.

```
br blocked [--json] [--limit N] [--detailed] [--type TYPE] [--priority P]
```

**Note**: `br blocked` does NOT support `--parent`. It lists all blocked issues globally.

## JSON Output Schema

Actual field names from live `br --json` output (snake_case):

### Task Object (from `br list --json`)

```json
{
  "id": "syml-9z7",
  "title": "Feature: template-builder",
  "description": "Spec: specs/001-template-builder/spec.md",
  "status": "open",
  "priority": 0,
  "issue_type": "epic",
  "owner": "user@example.com",
  "assignee": null,
  "created_at": "2026-01-19T19:05:35Z",
  "created_by": "User Name",
  "updated_at": "2026-01-19T19:05:35Z",
  "dependency_count": 0,
  "dependent_count": 0,
  "comment_count": 0
}
```

### Task Object with dependents (from `br show <id> --json`)

Additional fields on child/dependent objects:

```json
{
  "closed_at": "2026-01-19T19:38:52Z",
  "close_reason": "Completed requirements",
  "dependency_type": "parent-child"
}
```

### Key field notes

| Field              | Type    | Notes                                                                      |
| ------------------ | ------- | -------------------------------------------------------------------------- |
| `id`               | string  | Issue ID (e.g., `syml-9z7`)                                           |
| `priority`         | integer | 0-4, where 0 is highest                                                    |
| `issue_type`       | string  | NOT `type` — values: `task`, `bug`, `feature`, `epic`, `chore`, `decision` |
| `status`           | string  | `open`, `in_progress`, `blocked`, `deferred`, `closed`                     |
| `created_at`       | string  | ISO 8601 UTC timestamp                                                     |
| `dependency_count` | integer | Number of issues this depends on                                           |
| `dependent_count`  | integer | Number of issues that depend on this                                       |
| `dependents`       | array   | Present in `br show --json` output, contains child/dependent objects       |
| `close_reason`     | string  | Present when closed                                                        |

### Status Values

`open`, `in_progress`, `blocked`, `deferred`, `closed`

### List output vs show output

- `br list --json` returns a paginated envelope: `{"issues": [...], "total": N, "limit": N, "offset": N, "has_more": bool}` (use `.issues[]` in jq)
- `br show <id> --json` returns a bare array with full objects including nested `dependents` array (use `.[0]` in jq)
- `br ready --json`, `br blocked --json`, `br search --json` return bare arrays (use `.[]` in jq)

## Additional Commands

These commands are available in `br` (beads_rust):

| Command                          | Description                                                  |
| -------------------------------- | ------------------------------------------------------------ |
| `br stale`                       | Find stale issues (no activity for a configurable period)    |
| `br label`                       | Manage labels (create, list, rename, delete)                 |
| `br comments`                    | List comments on an issue                                    |
| `br comments add <id> "message"` | Add a comment to an issue                                    |
| `br doctor`                      | Diagnose and repair database issues                          |
| `br stats`                       | Show database and project statistics                         |
| `br upgrade`                     | Upgrade br to the latest version                             |
| `br agents`                      | Manage agent configurations                                  |
| `br reopen`                      | Reopen a previously closed issue                             |
| `br graph`                       | Visualize issue relationships as a graph                     |
| `br changelog`                   | Generate a changelog from closed issues                      |
| `br defer`                       | Defer an issue until a future date                           |
| `br undefer`                     | Remove deferral from an issue                                |
| `br lint`                        | Lint issues for common problems (missing descriptions, etc.) |
| `br orphans`                     | Find orphaned issues with no parent                          |
| `br schema`                      | Show or manage the database schema                           |
| `br where`                       | Show the database file path                                  |
| `br info`                        | Show project/database information                            |
| `br history`                     | Show change history for an issue                             |
| `br audit`                       | Show audit trail of operations                               |
