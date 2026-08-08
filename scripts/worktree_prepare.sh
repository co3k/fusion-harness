#!/usr/bin/env bash
# Create a disposable git worktree for a fusion run.
# Usage: worktree_prepare.sh <repo_abs> <run_id>
set -euo pipefail
REPO="${1:?repo abs path}"
RUN_ID="${2:?run_id}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
RUN_DIR="$HERMES_HOME/fusion/runs/$RUN_ID"
mkdir -p "$RUN_DIR"
cd "$REPO"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "not a git repo: $REPO" >&2
  exit 1
fi
BRANCH="fusion/${RUN_ID}"
# sibling directory to avoid nesting
PARENT="$(dirname "$REPO")"
BASE="$(basename "$REPO")"
WT="${PARENT}/.fusion-wt-${BASE}-${RUN_ID}"
if [[ -e "$WT" ]]; then
  echo "worktree path exists: $WT" >&2
  exit 1
fi
git worktree add "$WT" -b "$BRANCH"
echo "$WT" | tee "$RUN_DIR/worktree.txt"
echo "$BRANCH" | tee "$RUN_DIR/branch.txt"
echo "worktree=$WT branch=$BRANCH"
