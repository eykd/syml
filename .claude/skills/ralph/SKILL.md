---
name: ralph
description: Drain the beads ready queue from the user's current Claude Code session. The orchestrator runs the prep + verify bookkeeping scripts INLINE (their beads writes must persist in the main session) and dispatches one short-lived ralph-worker subagent per task. Replaces the old `claude -p` background loop. Use when you want autonomous task processing inside the subscription envelope.
---

# Ralph Orchestrator (single-session)

Ralph drains the beads ready queue **one task at a time** from the user's
current Claude Code session. Each iteration the orchestrator:

1. runs `.claude/skills/ralph/prep.sh` **inline** (its own Bash) to select and
   claim the next ready leaf;
2. dispatches a **single `ralph-worker` subagent** to implement that leaf; then
3. runs `.claude/skills/ralph/verify.sh` **inline** to confirm the close + HEAD
   advance, recovering the task if needed.

There is no daemon, no background process, no `claude -p` invocation, and no
`.ralph.lock` / `.ralph-monitor.json` state file. The session being visible to
the user **is** the monitor.

## Why prep and verify run inline (not as subagents)

prep and verify mutate beads state — claim, retire DONE grouping parents,
`br close`, reopen-on-failure, the `.beads/` flush commit. They run **inline in
the main session**, and only the **worker** is a subagent. Three reasons, in
order of how load-bearing they are:

1. **Orchestration can't live in a subagent.** prep/verify are part of the drain
   loop that dispatches the worker subagent; a subagent can't dispatch subagents,
   so the loop — and the bookkeeping interleaved with it — must run in the main
   conversation. This is the repo's standing rule and the only strictly necessary
   reason.
2. **Determinism.** prep/verify are committed shell scripts invoked as a single
   Bash command. A prose subagent improvises multi-step bash and would skip the
   leaf-selection logic; running the committed script inline guarantees it
   actually executes (see commit history: "so the leaf selector actually
   executes").
3. **One serialized writer.** Keeping every mutating `br` op in the single
   main-session flow avoids the concurrent-writer races the old `claude -p`
   multi-process loop hit (lock contention, lost updates). verify also trusts
   prep's captured pre-HEAD vs. the worker's reported post-HEAD instead of
   re-reading volatile git/beads state, so a stale read can't falsely reopen a
   task that did commit.

The worker stays a subagent because it carries heavy TDD context that must stay
out of the orchestrator, and its beads reads are of the **immutable** task body
(so staleness is harmless). Its one mutating write (`br close`) is confirmed by
verify via the HEAD-advance check above. Net rule: **beads bookkeeping in the
main session, leaf work in a subagent.**

> **Note — a persistence claim that no longer holds.** Earlier versions of this
> doc said a sandboxed subagent's `br` writes "do not persist/reflect" on the
> shared `.beads/beads.db`, and that this caused `br ready` to re-surface closed
> tasks. That was tested directly (2026-06-03) and **does not reproduce**: under
> `br` 0.1.45 (direct mode — `--no-daemon` is a documented no-op, there is no
> daemon cache) a default subagent shares the main session's filesystem and
> SQLite WAL, so a subagent's `br create`/`br close` is immediately visible to
> the next main-session `br` call (verified by probe: a subagent-created issue
> showed up in the main session's `br show`/`br count`/`br ready`). The
> re-surface loop was a determinism/serialization bug (reasons 2–3), not
> vanishing writes. Writes **would** be lost only if an agent were dispatched
> with git **worktree isolation** (separate `.beads/` — ralph does not do this)
> or under an older daemon-mode `br`. Do not refactor subagent `br` writes out on
> persistence grounds alone.

## Why this exists

Anthropic begins billing `claude -p` runs as overage on 2026-06-15. The old
ralph (`scripts/ralph.ts`) spawned a fresh `claude -p` child per task and is no
longer financially viable. This skill replaces it with an in-session
orchestrator: the heavy per-task work runs in a fresh subordinate **subagent**
(covered by the subscription), while the cheap deterministic bookkeeping runs as
two inline script calls. The orchestrator's own context grows by only a small
amount per task — two one-line script outputs plus the worker's dispatch prompt
and one-line reply.

## When to use

- `/sp:07-implement` invokes this skill after its preflight checks. The
  current branch (the feature's epic branch) drives scope detection
  automatically.
- `/ralph` invokes this skill directly for ad-hoc work. On a
  `NNN-feature-name` branch with a matching epic, it scopes to that epic;
  otherwise it drains every ready task.

## Do not use this skill for

- Single tasks. Just do them directly.
- Tasks requiring interactive decisions.
- Exploratory work without a clear acceptance criterion in beads.

## How it works

```
Orchestrator (this session)
   loop {
     ① run   bash prep.sh                     (inline) → "READY <id> SCOPE=<x> HEAD=<pre>" | "QUEUE EMPTY SCOPE=<x>"
     ② Agent(ralph-worker)                              → "OK <id> HEAD=<post>"            | "FAILED <id>: <reason>"
     ③ run   bash verify.sh <id> <pre> <post> (inline) → "VERIFIED"                       | "RECOVERED <id>"
     break if ① said "QUEUE EMPTY"
   }
```

The orchestrator runs Bash **only** to invoke `prep.sh` and `verify.sh` (and to
read their single-line output). It does no task work itself, reads/edits no
source files, and runs no other Bash — all of that belongs to the worker
subagent. `prep.sh` and `verify.sh` are committed, heavily-commented scripts that
hold every deterministic step — prep does scope detection, leaf classification,
DONE-parent retirement, claim, and HEAD capture; verify does the status check,
HEAD-advance net, reopen, and `.beads/` flush. Keeping the logic in committed
scripts also makes it run identically regardless of model — an earlier prose
version of prep was improvised by subagents into `br ready | head -n1`, grabbing
a `US<N>:` grouping **parent** instead of its first **leaf**.

## Completion signal: the worker line, never the notification envelope

The worker's result arrives in a `<task-notification>`. Trust **only** the
one-line body contract (`OK <id> HEAD=<sha>` / `FAILED <id>: <reason>`) and the
`<id>` / `HEAD=<sha>` parsed _from inside that line_ — never the notification's
`<task-id>` envelope, and never a correlation between the `agentId` returned when
you dispatched the worker and any notification id. Notification envelopes have
been observed to mis-attribute (a rest event stamped with a previous agent's
task-id, or a body that is a stale duplicate of another agent's report) **even
under strict one-at-a-time dispatch**. Ralph is already immune by construction —
it dispatches exactly one worker per iteration, and `verify.sh` re-derives truth
from `prepHead` vs the worker-reported `workerHead` plus `br show <id>` status, so
a mis-stamped envelope cannot corrupt the loop — but do **not** add any logic
that keys off a notification's task-id or an agentId. If the worker's reported
HEAD and a notification ever disagree, the worker line (validated by verify) wins.

## Orchestration prompt

Run this prompt verbatim in the current session (no slash-command needed — you
ARE the orchestrator once this skill is invoked):

```
You are the ralph orchestrator for this session. Drain the beads ready queue by,
each iteration: running prep.sh inline, dispatching one worker subagent, then
running verify.sh inline — in strict sequence, until prep reports the queue is
empty.

The ONLY Bash you run is `bash .claude/skills/ralph/prep.sh` and
`bash .claude/skills/ralph/verify.sh ...`. You do NOT read or edit source files,
implement tasks, or run any other Bash — that is the worker subagent's job. prep
and verify run inline here (not as subagents) because they are part of the loop
that dispatches the worker (orchestration can't run in a subagent) and are
deterministic committed scripts; keeping every `br` write in this one session
also serializes them.

State variables you maintain in your head (NOT in files):
  - lastPrepId: the task ID prep returned last iteration (or null)
  - sameIdRepeats: how many consecutive iterations prep returned the same id
  - iterationCount: total iterations so far
  - prepHead: the pre-work <sha> from prep's "HEAD=<sha>" (may be "NONE")
  - workerHead: the post-work <sha> from the worker's "HEAD=<sha>" ("NONE" on FAILED)

Loop:

1. Run via Bash: bash .claude/skills/ralph/prep.sh
   Its stdout is exactly one line: "READY <id> SCOPE=<x> HEAD=<sha>" or
   "QUEUE EMPTY SCOPE=<x>". (Ignore any stderr; trust the single stdout line.)
   - If iterationCount == 0: announce the chosen scope to the user verbatim
     ("Draining scope: <x>") so they can ^C if it's wrong.
   - If "QUEUE EMPTY": announce "Queue drained (scope=<x>)" and stop.
   - Parse the trailing "HEAD=<sha>" into prepHead.
   - If <id> == lastPrepId: increment sameIdRepeats. If sameIdRepeats >= 2,
     stop and surface to the user: "Hot loop on <id> — stopping. Investigate
     manually." Otherwise continue.
   - Else: set lastPrepId = <id>, sameIdRepeats = 1.

2. Dispatch: Agent(subagent_type="ralph-worker", description="ralph worker tick",
                   prompt="Implement task <id>.")
   Reply will be exactly "OK <id> HEAD=<sha>" or "FAILED <id>: <one-line>".
   - On "OK <id> HEAD=<sha>": parse the trailing "HEAD=<sha>" into workerHead.
   - On "FAILED ...": set workerHead = "NONE".

3. Run via Bash: bash .claude/skills/ralph/verify.sh <id> <prepHead> <workerHead>
   (Substitute the actual task id and the two shas. verify proves HEAD advanced
   by comparing them — it never re-reads HEAD itself.)
   Its stdout is exactly one line: "VERIFIED" or "RECOVERED <id>".

4. Speak one short line to the user (e.g. "✓ <id>" on VERIFIED,
   "↻ <id> recovered" on RECOVERED, "✗ <id>: <reason>" on FAILED-not-recovered).
   No commentary, no analysis, no plans.

5. Increment iterationCount. Goto 1.
```

## Scope detection

`prep.sh` re-detects the scope every iteration:

1. Read `git branch --show-current`.
2. Strip leading `NNN-` digits, lowercase, replace hyphens with spaces.
3. Search `br list --type epic --status open --json` for an epic whose title
   (also lowercased / hyphens→spaces) contains that string.
4. If matched → scope = that epic ID, drain only its recursive descendants.
5. Otherwise → scope = `ALL`, drain every ready task.

Switching branches mid-run automatically follows the new branch's scope.

## Failure modes the orchestrator handles

| Symptom                                                | Resolution                                                                                                                                                                                                                                                              |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| worker returns `FAILED <id>: ...`                      | the inline `verify.sh` releases the claim + leaves a FAILED comment; orchestrator moves on (next prep tick)                                                                                                                                                             |
| prep returns the same `<id>` twice                     | hot-loop guard fires; orchestrator stops and surfaces                                                                                                                                                                                                                   |
| prep reports `QUEUE EMPTY` while tasks are still ready | epic descendants are _dependents_ — scope query uses `br dep tree --direction up` (not `down`); plus repair + re-query once before trusting empty (prep.sh step 4)                                                                                                      |
| prep re-surfaces an already-closed task                | fixed by running prep/verify inline as committed scripts — a determinism + one-serialized-writer fix, NOT a subagent-persistence issue (a default subagent's beads writes _do_ reflect in the main session; verified 2026-06-03) — see "Why prep and verify run inline" |
| prep returns `QUEUE EMPTY`                             | orchestrator announces "Queue drained" and stops                                                                                                                                                                                                                        |
| user `^C`                                              | session ends; no daemon to kill, no lockfile to clean                                                                                                                                                                                                                   |

## What goes away vs. the old ralph

- `scripts/ralph.ts` + `scripts/ralph/`
- `.ralph.lock`, `.ralph.log`, `.ralph.exit`, `.ralph-monitor.json`
- The 8-status monitor classifier (DONE/CRASHED/STRANDED/ZOMBIE/HOT_LOOP/…)
- The 15-minute `ScheduleWakeup` chain
- All `claude -p` invocations

## RED-task commits

Task chains stay split into Red/Green/Refactor. A **RED** task (title `^Red:`)
self-commits its known-failing test via
`.venv/bin/python -m tools.commit_red <id>`: the script confirms the
staged test fails, runs the full pre-commit hook (the pytest-check hook is
skipped via `SKIP=pytest-check`; ruff, mypy, and uv-lock still run), commits
locally with `[skip ci]`, and does **not** push. The following Green task's `git push` lands the RED
commit as a non-tip ancestor, so the branch tip is always green and CI never
sees a red push. The script is RED-task-only — it refuses on any other task
and is never a `--no-verify` bypass. The verify step's HEAD-advance net then
holds uniformly: every closed, non-exempt task must have produced a commit.
verify proves this by comparing prep's pre-work HEAD (`prepHead`) against the
worker's reported post-work HEAD (`workerHead`) — it never re-reads HEAD itself,
so a stale read can no longer falsely reopen a task that really did commit,
while a genuine no-op close (worker reports `post == pre`) is still caught.

## What stays the same

- Beads is still the single source of truth for task state.
- Ralph operates at **leaf** granularity — one Red/Green/Refactor/acceptance
  task per iteration. The `US<N>:` parent is a pure grouping node: it is **never
  worked**, only retired (auto-closed by prep.sh) once all its children close.
  ATDD's outer loop is not run as a single outer-loop invocation on the parent; it
  is expressed by the chain's bookend leaves (the `Write acceptance test` leaf at
  the start and the `Verify acceptance test passes` leaf at the end), with TDD
  Red/Green/Refactor leaves in between. The chain shape from `/sp:05-tasks` and
  `/beads-task-chains` is unchanged — only prep's selection (leaf, not parent)
  and the worker's routing (per-leaf, not per-slice) changed. **Carve-out:** a
  worker may _add_ a discovered Red/Green/Refactor sub-chain under a US story at
  runtime (see `/beads-task-chains` → "Conservative discovery") — an allowed
  runtime addition that grows the chain but does not alter its shape; the new
  leaves keep the `US<N>:` parent open until they close.
- The per-leaf TDD workflow is unchanged; it just runs inside the
  `ralph-worker` subagent now, routed by leaf title.
- Commit + `br close` happen once per task, in order. Every task except RED
  (and assertion-only acceptance-verify leaves) also pushes; a RED task commits
  locally and the next Green push carries it.
- `/sp:07-implement` is still the spec-kit entry point; it now calls this
  skill in-session after its preflight checks instead of spawning a daemon.

## Examples

### Drain the current branch's epic

```
/ralph
```

(Assuming you're sitting on `012-auth-static-integration` and there is an
open epic with `auth static integration` in its title.)

### Drain every ready task across the repo

```
git checkout master
/ralph
```

(No matching epic on `master` → scope falls back to `ALL`.)
