#!/usr/bin/env bash
# Find the beads epic (or its implement child) for the current branch.
#
# Ralph and ad-hoc task creation find epics by stripping the leading digits
# from the branch name (e.g. `012-auth-static-integration` →
# `auth-static-integration`) and matching against open epic titles
# (case-insensitive, hyphens = spaces).
#
# Usage:
#   epic=$(scripts/find-branch-epic.sh)              # epic ID
#   impl=$(scripts/find-branch-epic.sh --implement)  # [sp:07-implement] child ID
#
# Exits 1 with a message on stderr when no matching epic (or implement child)
# is found.
set -euo pipefail

mode="epic"
if [[ "${1:-}" == "--implement" ]]; then
  mode="implement"
fi

branch=$(git branch --show-current | sed 's/^[0-9]*-//')

epic=$(br list --type epic --status open --json |
  jq -r --arg b "$branch" \
    '.issues[]
     | select(.title | ascii_downcase | gsub("-";" ")
       | contains($b | ascii_downcase | gsub("-";" ")))
     | .id' | head -n1)

if [[ -z "$epic" ]]; then
  echo "find-branch-epic: no open epic matches branch feature '$branch'" >&2
  exit 1
fi

if [[ "$mode" == "epic" ]]; then
  echo "$epic"
  exit 0
fi

impl=$(br show "$epic" --json |
  jq -r '.[0].dependents[] | select(.title | contains("[sp:07-implement]")) | .id' |
  head -n1)

if [[ -z "$impl" ]]; then
  echo "find-branch-epic: epic $epic has no [sp:07-implement] child" >&2
  exit 1
fi

echo "$impl"
