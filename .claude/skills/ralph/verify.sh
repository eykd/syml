#!/usr/bin/env bash
# ralph-verify — one verify tick for the ralph orchestration loop.
#
# Usage: verify.sh <task-id> <pre-HEAD> <post-HEAD>
#   <task-id>   the task the worker just ran
#   <pre-HEAD>  prep's pre-work HEAD (or the literal NONE)
#   <post-HEAD> the HEAD the worker reported after committing (or NONE)
#
# Prints EXACTLY one line on stdout:
#   VERIFIED
#   RECOVERED <task-id>
#
# It confirms the task is closed AND that HEAD advanced — by comparing <pre-HEAD>
# against <post-HEAD>, NOT by re-reading HEAD itself. Both shas were captured by
# the agents that did the work (prep before, worker after), so a stale
# verify-side `git rev-parse` can no longer falsely reopen a task that really
# committed. A genuine no-op close (worker reports post == pre, or NONE) is still
# caught. Some titles legitimately close without a commit and are exempt.
#
# WHERE THIS RUNS — THE ORCHESTRATOR'S MAIN SESSION, NOT A SUBAGENT (see prep.sh
# for the full rationale): verify mutates beads on the recover path (reopen +
# FAILED comment) and commits the .beads/ flush, and beads writes do not persist
# reliably from a sandboxed subagent's Bash. The orchestrator runs this script
# inline, once per iteration, with the three values it already holds (the task
# id, prep's pre-HEAD, the worker's reported post-HEAD), and reads one line.

# Deliberately no `set -e`: the flow relies on `|| true` guards and must always
# fall through to a single contract line.

ID="${1:-}"
PRE="${2:-NONE}"
POST="${3:-NONE}"

if [ -z "$ID" ]; then
  echo "RECOVERED unknown"
  exit 0
fi

# Flush any stray .beads/ changes left behind by br operations, but ONLY when
# .beads/ is the only dirty area — let any other drift surface to the next
# prep tick. (This tests dirty-state, never a HEAD read.)
flush_beads() {
  if [ -n "$(git status --porcelain .beads/)" ] \
     && [ -z "$(git status --porcelain | grep -v '^...\.beads/')" ]; then
    git add .beads/ >/dev/null 2>&1 || true
    git commit -m "chore(beads): sync state" >/dev/null 2>&1 || true
  fi
}

# Release the claim so the task rejoins the ready queue (or stays blocked on
# whatever sub-tasks it filed).
#
# One `br doctor --repair` retry, logged to stderr rather than swallowed. The
# blind double-repair this replaced worked around a cross-process WAL
# checkpoint race in br < 0.5.5 (beads_rust#457); on >= 0.5.5 a failing repair
# is a real signal (a rebuild after prior failed recovery evidence needs
# --allow-repeated-repair).
reopen() {
  br update "$ID" --status open >/dev/null 2>&1 && return 0
  br doctor --repair >/dev/null 2>"${TMPDIR:-/tmp}/ralph-verify-repair.err" \
    || echo "ralph-verify: br doctor --repair failed: $(tr '\n' ' ' < "${TMPDIR:-/tmp}/ralph-verify-repair.err")" >&2
  br update "$ID" --status open >/dev/null 2>&1 \
    || echo "ralph-verify: could not reopen $ID after repair" >&2
}

STATUS=$(br show "$ID" --json 2>/dev/null | jq -r '.[0].status' 2>/dev/null)
TITLE=$(br show "$ID" --json 2>/dev/null | jq -r '.[0].title' 2>/dev/null)

if [ "$STATUS" = "closed" ]; then
  # Exemptions: a no-op Refactor or an assertion-only acceptance gate close
  # legitimately without a commit. Skip the HEAD-advance assertion.
  if printf '%s' "$TITLE" | grep -Eiq '^(Refactor:|Verify acceptance test passes)'; then
    flush_beads
    echo "VERIFIED"
    exit 0
  fi

  # HEAD-advance net: a closed, non-exempt task must have produced a commit.
  # Reopen when the worker reported no commit (post == NONE) or its post-work
  # HEAD equals prep's pre-work HEAD (post == pre, a real no-op close). No
  # `git rev-parse` here: the comparison uses only the passed-in values, so it
  # cannot race on a stale read.
  if [ "$POST" = "NONE" ] || [ "$POST" = "$PRE" ]; then
    reopen
    br comments add "$ID" "FAILED: closed without a commit (HEAD did not advance)" \
      >/dev/null 2>&1 || true
    echo "RECOVERED $ID"
    exit 0
  fi

  # HEAD advanced. Flush bookkeeping and confirm.
  flush_beads
  echo "VERIFIED"
  exit 0
fi

# Not closed: the worker returned FAILED, crashed, or the task id doesn't exist.
# Release the claim, leave a comment, flush, and recover.
reopen
br comments add "$ID" "FAILED: orchestrator detected unfinished work (status was ${STATUS:-unknown})" \
  >/dev/null 2>&1 || true
flush_beads
echo "RECOVERED $ID"
exit 0
