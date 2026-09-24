---
name: sp-orchestrator
description: Use when (1) driving a multi-step or multi-phase task from the main session, (2) a task would otherwise fill the main context window with file dumps or tool output, (3) planning work that fans out across independent pieces, or (4) running the sp:* workflow via /sp:shepherd. Defines what to delegate, what must stay inline, and how to pick a model per subagent.
---

# Orchestrator

Act as orchestrator: delegate the _leaf_ work to subagents aggressively so the
main context window stays small, and keep the decisions, the sequencing, and the
result-checking here.

## What to delegate

Anything whose value is a conclusion rather than its raw output: searching
across many files, reading a subsystem to answer one question, implementing a
single well-scoped task, running a review pass. Relay what matters from the
subagent's report — its output is not shown to the principal.

Assign each subagent the cheapest model that can do its job (`model: "sonnet"`
or `"haiku"` for mechanical or search-shaped work); reserve the strongest model
for analysis that genuinely needs it. Do not pin a specific model name in prose
here or in a subagent prompt; use the alias.

## What must NOT be delegated

**Orchestration itself.** Subagents cannot spawn subagents. Any loop that fans
out per-task work must run in the main conversation:

- `/ralph`, and therefore `/sp:07-implement` and `/sp:08-harden`, which dispatch
  a `ralph-worker` per task
- `/sp:next`, which claims a beads task and then invokes the phase command
- `/sp:shepherd`, which drives the whole `sp:*` sequence

Delegating any of these collapses the fan-out into one long-running subagent
context, and its beads writes do not persist to the main session. See
`.claude/skills/ralph/SKILL.md` → "Why prep and verify run inline" for the
canonical rationale.

**Beads bookkeeping in a fan-out loop.** `br` writes that the loop depends on
(claims, closes, prep/verify) run inline so they serialize and persist.

## Verifying subagent work

Do not accept a completion report at face value. Decide what happened from
durable side-effects — files on disk, test output, beads state — rather than
from the subagent's summary or the `<task-notification>` envelope.

## Teammate lifecycle

Named teammates stay resumable by name after they finish; a later `SendMessage`
picks up their transcript. Do not originate a `shutdown_request` unless the
principal asks for it — the SendMessage contract reserves that for explicit
requests.
