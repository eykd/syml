---
name: sp-security-review
description: Security review of all branch changes (base..HEAD). Runs the /security-audit skill, classifies findings, creates remediation tasks or appends implementation constraints. Writes .sp-harden-findings.json so orchestrators (/sp:08-harden) can count p1/p2 findings.
tools: Read, Grep, Glob, Bash, Edit, Write, Skill
model: opus
---

## Scope

Review scope is **all branch changes from the base branch (usually `master` or `main`) to `HEAD`**.

Determine base branch:

1. Try:

```bash
git symbolic-ref --short refs/remotes/origin/HEAD | sed 's|^origin/||'
```

2. If that fails, choose the first existing branch in this order:

- `main`
- `master`

Verify it exists locally/remotely:

```bash
git show-ref --verify --quiet refs/heads/<base> || git show-ref --verify --quiet refs/remotes/origin/<base>
```

Compute the review range:

- `<base>..HEAD`

## Steps

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and parse `FEATURE_DIR` (absolute path).

2. Retrieve the current epic id:

```bash
grep "Beads Epic" FEATURE_DIR/spec.md | grep -oE 'syml-[a-z0-9]+'
```

If no epic id is found, ERROR with: "No Beads Epic found for this feature. Run `/sp:02-specify` first."

3. List current open + in_progress tasks for the epic (for de-duplication):

```bash
br show <epic-id> --json | jq '.[0].dependents[] | select(.status == "open")'
br show <epic-id> --json | jq '.[0].dependents[] | select(.status == "in_progress")'
```

4. Identify changed files and summary:

```bash
git diff --name-only <base>..HEAD
git diff --stat <base>..HEAD
```

5. Run the review skill over this change set:

- Skill: `/security-audit`
- Review range: `<base>..HEAD`
- Focus: security vulnerabilities in a parsing library that consumes untrusted
  input. The relevant classes here are: unbounded recursion or deeply-nested
  input driving a `RecursionError` or stack exhaustion; catastrophic
  backtracking / regex DoS in the Parsimonious PEG grammar or any `re` pattern;
  unbounded memory growth from pathological documents (very long lines, huge
  indentation runs, enormous node trees); file handling in `syml.load` (path
  traversal, encoding assumptions, leaked handles, reading without a size
  bound); exceptions that leak absolute paths or source text into messages; and
  any use of `eval`, `exec`, pickle, or subprocess on parsed content. Web,
  HTTP, and database concerns do not apply to this repo — do not invent them.
- **Style Requirements**:
  - Report problems only, never praise or positive feedback
  - Make findings scannable in 30 seconds
  - Format: file:line, severity, one-sentence problem, concise fix
  - Include copy-paste prompt ONLY if findings exist (3-5 lines)

If the skill supports reading the git diff directly, prefer providing it the diff for `<base>..HEAD`.

6. Translate findings into beads tasks:

For each distinct finding:

**Step A — Classify the finding (do this first):**

Check whether the target file(s) referenced in the finding exist on the current branch:

```bash
git show HEAD:<file-path> 2>/dev/null && echo "exists" || echo "not-yet-written"
```

- **File does NOT exist on HEAD** → This is a **design constraint**, not an independent fixable issue. The code hasn't been written yet; implementing a standalone task forces a build-wrong-then-fix cycle.
  - Identify the US story task that will own this code:
    ```bash
    br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | test("^US[0-9]+:")) | {id, title}'
    ```
  - Append the finding to that US story's description as an `## Implementation Constraints` entry:
    ```bash
    br update <us-story-id> --description "<current-description>
    ```

---

## Implementation Constraints (from [sp:security-review])

**[SEVERITY] <short title>**
Problem: <what is wrong>
Fix: <concrete steps to implement it correctly from the start>"

````

- Do **NOT** create a standalone task for this finding. Stop here for this finding.

- **File DOES exist on HEAD** → This is an **independent fix** on pre-existing code. Continue to Steps B and C.

**Step B — Check for duplicates (pre-existing files only):**

- Check if an existing task already covers it (match by keywords + file path).

**Step C — Create task (pre-existing files only, if not already covered):**

- Create a new task under the epic:

```bash
br create "Remediate: <short finding title>" -p <1|2|3> --parent <epic-id> \
  --description "**Review**: [sp:security-review]\n**Range**: <base>..HEAD\n**Files**: <file paths>\n\n**Finding**:\n<what's wrong>\n\n**Fix suggestion**:\n<concrete steps>\n\n**Acceptance**:\n- <verifiable criteria>" --json
````

Severity → priority mapping:

- CRITICAL security/architecture correctness → p1
- MAJOR → p2
- MINOR/nits → p3

7. Cross-reference with Prior Learnings:

   Search `.specify/solutions/` for solutions matching current finding categories. If the directory does not exist, skip this step silently.
   - Search `.specify/solutions/security/` and `.specify/solutions/clean-architecture/` for solutions related to current findings
   - If an implementation repeats a previously solved pattern, note it in the remediation task description with a reference to the original solution document
   - Example addition to task description: `\n\n**Prior Learning**: See .specify/solutions/security/{slug}.md for a previous solution to this pattern.`

8. Write structured findings file for orchestrators:

   Before the human-readable summary, write `.sp-harden-findings.json` so an orchestrator (e.g., `/sp:08-harden`) can count p1/p2 findings without parsing prose. Overwrite any existing file.

   Build the findings array, write it to a JSON file, and pipe it into the
   fingerprint tool. Never hash by hand — the tool owns the algorithm, so every
   phase produces fingerprints an orchestrator can compare across cycles.

   ```text
   # One entry per standalone task created above, in the SAME order as the tasks
   # were filed.
   #   category  = the finding's category slug
   #   file      = the repo-relative path the finding is in (e.g. src/syml/nodes.py)
   #   title     = the task title exactly as filed
   #   severity  = CRITICAL | MAJOR | MINOR (drives criticalCount / highCount /
   #               mediumCount and the 1/2/3 priorities in the output)
   #   line      = the line number the finding anchors to, or null
   #   task_id   = the beads ID of the standalone task filed for this finding
   # Implementation Constraints appended to US tasks do NOT appear here (they are
   # not independent fixable items) and do not count toward any total.
   ```

   Write the array with the `Write` tool to `FEATURE_DIR/.sp-findings.json`
   (not a shell heredoc — the indentation in this document would break the
   terminator), then pipe that file in. Shape:

   ```json
   [
     {
       "category": "<category>",
       "file": "<repo-relative path>",
       "title": "<task title>",
       "severity": "CRITICAL",
       "line": <line-number-or-null>,
       "task_id": "<beads-task-id>"
     }
   ]
   ```

   ```bash
   .venv/bin/python -m tools.harden_fingerprint --phase security-review < FEATURE_DIR/.sp-findings.json
   ```

   The tool writes `.sp-harden-findings.json` (overwriting any existing file)
   with `phase`, `criticalCount`, `highCount`, `mediumCount`, `taskIds`,
   `fingerprints`, `priorities`, and `timestamp`. Each fingerprint is
   `sha1("|".join([category, file, normalize(title)]))`, where `normalize`
   lowercases, strips every character outside `[a-z0-9\s]`, collapses runs of
   whitespace to single spaces, and trims.

   If no tasks were created (review was clean), still run the tool with an empty
   array so the file is always present after this agent runs:

   ```bash
   echo '[]' | .venv/bin/python -m tools.harden_fingerprint --phase security-review
   ```

9. Output a concise human-readable summary:

- Base branch used
- Number of findings
- Number of new tasks created (broken down by priority: p1 / p2 / p3)
- List created task IDs + titles
- If remediation tasks were created, include: "Consider running `/compound` to document what you learned fixing these issues."

## Commit Changes

Run the `/sp-commit` skill to stage and commit all changes made during this phase. Do not push.

Note: `.sp-harden-findings.json` is intentionally **not** committed — it is a transient orchestration artifact. Ensure it is listed in `.gitignore` (or that the `/sp-commit` skill excludes it).

---

You are a subagent: do all work inline in your own context. You cannot dispatch further subagents, so never attempt to delegate — there is no Agent/Task tool available to you.
