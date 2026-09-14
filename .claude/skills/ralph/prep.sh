#!/usr/bin/env bash
# ralph-prep — one prep tick for the ralph orchestration loop.
#
# Resets a dirty working tree, repairs the beads SQLite index, detects the
# orchestration scope from the current branch, selects the next ready LEAF task
# (skipping ACTIVE grouping parents and retiring DONE ones), claims it, and
# prints EXACTLY one line on stdout:
#
#   READY <task-id> SCOPE=<epic-id-or-ALL> HEAD=<sha>
#   QUEUE EMPTY SCOPE=<epic-id-or-ALL>
#
# On any unrecoverable error it still prints one line — QUEUE EMPTY SCOPE=ERROR
# — so the orchestrator treats the queue as drained. All br/git/jq chatter is
# redirected to /dev/null or stderr; stdout carries the contract line and
# nothing else.
#
# WHERE THIS RUNS — THE ORCHESTRATOR'S MAIN SESSION, NOT A SUBAGENT:
# The ralph orchestrator invokes this script INLINE via its own Bash tool, once
# per iteration, and reads the single contract line. prep is NOT a subagent.
# Two hard reasons, both learned the hard way:
#   1. PERSISTENCE/FRESHNESS. beads.db is a local, gitignored SQLite store
#      (JSONL is the git-tracked truth; br auto-imports/auto-flushes between
#      them). In a sandboxed subagent's Bash, prep's mutating beads ops (claim,
#      `br close` of DONE parents, `br doctor --repair`) and/or its reads do not
#      reflect/persist consistently, so `br ready` kept surfacing tasks that
#      were already closed — an infinite re-surface. The main session's Bash
#      persists these writes; running prep there fixed the drain. Mutable beads
#      bookkeeping MUST run in the main session.
#   2. DETERMINISM. Earlier the selection logic lived as a multi-step bash block
#      inside a prose-driven subagent's Markdown, and the subagent improvised it
#      (effectively `br ready | head -n1`), grabbing a `US<N>:` grouping PARENT
#      instead of its first leaf. A committed script runs the classifier
#      identically every time. The orchestrator just runs it and reads one line.
#
# WHY LEAVES, NOT PARENTS:
# A `parent-child` edge does not block, so `br ready` surfaces a grouping parent
# AND its first child together. A leaf has zero parent-child dependents. The
# classifier (pc_state) distinguishes:
#   total == 0           -> LEAF   (claimable work; pick it, stop)
#   total > 0, open > 0  -> ACTIVE (skip; its ready child is later in the list)
#   total > 0, open == 0 -> DONE   (retire it; beads has no parent auto-close)
#
# Note on scope: beads stores parent->child as a `parent-child` dependency edge
# pointing from child to epic, so an epic's descendants are its DEPENDENTS —
# reachable via `br dep tree --direction up`, not `down`. `down` returns only
# what the epic waits on (usually nothing) and yields a false QUEUE EMPTY.

# Deliberately no `set -e`: the flow relies on `|| true` guards and must always
# fall through to a single contract line.

# Temp dir for the candidate JSON. Prefer $TMPDIR — a sandboxed main session may
# only permit writes under $TMPDIR (and `.`), not a bare /tmp.
TMP="${TMPDIR:-/tmp}"

# --- 1. Reset the working tree if dirty (ignore .beads/ churn) --------------
DIRTY=$(git status --porcelain | grep -v '^...\.beads/' || true)
if [ -n "$DIRTY" ]; then
  just fix >/dev/null 2>&1 || true
  STILL_DIRTY=$(git status --porcelain | grep -v '^...\.beads/' || true)
  if [ -n "$STILL_DIRTY" ]; then
    # shellcheck disable=SC2046  # intentional: split the file list into separate `--` pathspec args
    git stash push -u -m "ralph-prep auto-stash $(date -u +%Y%m%dT%H%M%SZ)" -- \
      $(git status --porcelain | grep -v '^...\.beads/' | awk '{print $2}') \
      >/dev/null 2>&1 || true
  fi
fi

# --- 2. Repair the beads SQLite index (once, logged) -------------------------
# Runs `br doctor --repair` a single time and logs a failure to stderr instead
# of swallowing it. The blind `repair || repair || true` this replaced was a
# workaround for a cross-process WAL checkpoint race in br < 0.5.5
# (beads_rust#457) that could silently drop issues and dependency edges. On
# br >= 0.5.5 a failing repair is a real signal the orchestrator should see
# (a rebuild after prior failed recovery evidence needs --allow-repeated-repair).
repair_beads() {
  if ! br doctor --repair >/dev/null 2>"$TMP/ralph-repair.err"; then
    echo "ralph-prep: br doctor --repair failed: $(tr '\n' ' ' < "$TMP/ralph-repair.err")" >&2
    return 1
  fi
}
repair_beads || true

# --- 3. Detect orchestration scope ------------------------------------------
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
NEEDLE=$(printf '%s' "$BRANCH" | sed -E 's/^[0-9]+-//' | tr '[:upper:]' '[:lower:]' | tr '-' ' ')
SCOPE=$(br list --type epic --status open --json 2>/dev/null \
  | jq -r --arg n "$NEEDLE" '
      .issues[]
      | select(((.title // "") | ascii_downcase | gsub("-"; " ")) | contains($n))
      | .id' 2>/dev/null \
  | head -n1)
SCOPE=${SCOPE:-ALL}

# --- 4. Build candidates, classify, select the first true LEAF --------------
build_candidates() {
  # --limit 0 (unlimited): the default --limit 20 truncates the page before
  # the epic filter below runs, so once >=20 stale open epics outrank a scope's
  # real leaf tasks by priority sort, every candidate leaf gets starved out and
  # this reports a false QUEUE EMPTY. Unlimited + client-side filtering is the
  # only way to guarantee real candidates aren't dropped by pagination.
  br ready --sort priority --limit 0 --json > "$TMP/ralph-ready.json" 2>/dev/null || echo '[]' > "$TMP/ralph-ready.json"
  if [ "$SCOPE" = "ALL" ]; then
    jq -r '
      map(select(.issue_type != "epic"
        and ((.title // "") | startswith("[sp:") | not)))
      | .[].id' "$TMP/ralph-ready.json" 2>/dev/null
  else
    br dep tree "$SCOPE" --direction up --json > "$TMP/ralph-scope.json" 2>/dev/null || echo '{}' > "$TMP/ralph-scope.json"
    jq -r '.. | objects | .id? // empty' "$TMP/ralph-scope.json" 2>/dev/null | sort -u > "$TMP/ralph-scope-ids.txt"
    jq -r --slurpfile scope <(jq -R . "$TMP/ralph-scope-ids.txt" | jq -s .) '
      map(select(.issue_type != "epic"
        and ((.title // "") | startswith("[sp:") | not)))
      | .[]
      | select(.id as $id | ($scope[0] | index($id)))
      | .id' "$TMP/ralph-ready.json" 2>/dev/null
  fi
}

# Classify a candidate by its direct parent-child dependents.
pc_state() {  # LEAF | ACTIVE | DONE
  local s
  s=$(br show "$1" --json 2>/dev/null | jq -r '
    [.[0].dependents[]? | select(.dependency_type=="parent-child")] as $pc
    | "\($pc|length) \([$pc[]|select(.status=="closed"|not)]|length)"' 2>/dev/null)
  read -r total open <<<"$s"
  if [ "${total:-0}" -eq 0 ]; then echo LEAF
  elif [ "${open:-0}" -gt 0 ]; then echo ACTIVE
  else echo DONE; fi
}

# Scan priority-ordered candidates; claim the first LEAF, retire DONE grouping
# nodes as we pass them, skip ACTIVE parents (their ready child is later in the
# same list).
select_leaf() {
  while read -r id; do
    [ -z "$id" ] && continue
    case "$(pc_state "$id")" in
      LEAF)   echo "$id"; return 0 ;;
      ACTIVE) : ;;
      DONE)   br close "$id" --reason "grouping node complete (all child tasks closed)" >/dev/null 2>&1 || true ;;
    esac
  done
}

NEXT_ID=$(build_candidates | select_leaf)

# `br ready` / the dep-tree scope query can also read a stale SQLite index and
# report empty while tasks are still ready. Before trusting an empty result,
# repair the index and re-query once — only a confirmed-empty second pass counts
# as QUEUE EMPTY.
if [ -z "$NEXT_ID" ]; then
  repair_beads || true
  NEXT_ID=$(build_candidates | select_leaf)
fi

# --- 5. Claim it (or report empty) ------------------------------------------
if [ -z "$NEXT_ID" ]; then
  echo "QUEUE EMPTY SCOPE=$SCOPE"
  exit 0
fi

if ! br update "$NEXT_ID" --status in_progress >/dev/null 2>&1; then
  # Retry once after a repair in case of SQLite index drift.
  repair_beads || true
  if ! br update "$NEXT_ID" --status in_progress >/dev/null 2>&1; then
    echo "QUEUE EMPTY SCOPE=ERROR"
    exit 0
  fi
fi

# Capture the pre-work HEAD so verify can prove the worker produced a commit.
HEAD_SHA=$(git rev-parse HEAD 2>/dev/null || echo NONE)
echo "READY $NEXT_ID SCOPE=$SCOPE HEAD=$HEAD_SHA"
