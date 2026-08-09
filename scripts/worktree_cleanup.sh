#!/usr/bin/env bash
# Remove a disposable fusion worktree created by worktree_prepare.sh.
# Usage:
#   worktree_cleanup.sh <run_id>
#   worktree_cleanup.sh <repo_abs> <run_id>
# Prefers paths recorded under $HERMES_HOME/fusion/runs/<run_id>/.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

if [[ $# -eq 1 ]]; then
  RUN_ID="$1"
  REPO=""
elif [[ $# -eq 2 ]]; then
  REPO="$1"
  RUN_ID="$2"
  while [[ "$REPO" == */ ]]; do REPO="${REPO%/}"; done
  if [[ -n "$REPO" && "$REPO" != /* ]]; then
    echo "REPO must be an absolute path (got: $REPO)" >&2
    exit 1
  fi
else
  echo "Usage: $0 <run_id> | $0 <repo_abs> <run_id>" >&2
  exit 2
fi

if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "run_id must match ^[A-Za-z0-9._-]+\$ (got: $RUN_ID)" >&2
  exit 1
fi

RUN_DIR="$HERMES_HOME/fusion/runs/$RUN_ID"
WT=""
BRANCH=""
if [[ -f "$RUN_DIR/worktree.txt" ]]; then
  WT="$(tr -d '\r\n' <"$RUN_DIR/worktree.txt")"
fi
if [[ -f "$RUN_DIR/branch.txt" ]]; then
  BRANCH="$(tr -d '\r\n' <"$RUN_DIR/branch.txt")"
fi
if [[ -z "$REPO" && -f "$RUN_DIR/repo.txt" ]]; then
  REPO="$(tr -d '\r\n' <"$RUN_DIR/repo.txt")"
fi
if [[ -z "$BRANCH" ]]; then
  BRANCH="fusion/${RUN_ID}"
fi

if [[ -z "$REPO" ]]; then
  echo "repo unknown: pass <repo_abs> or ensure $RUN_DIR/repo.txt exists" >&2
  exit 1
fi
if [[ ! -d "$REPO" ]]; then
  echo "REPO is not a directory: $REPO" >&2
  exit 1
fi

cd "$REPO"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "not a git repo: $REPO" >&2
  exit 1
fi

if [[ -n "$WT" && -e "$WT" ]]; then
  git worktree remove --force "$WT" 2>/dev/null || git worktree remove "$WT"
  echo "removed worktree: $WT"
elif [[ -n "$WT" ]]; then
  echo "worktree path missing (already gone?): $WT"
  git worktree prune || true
else
  echo "no worktree.txt; pruning stale worktrees only"
  git worktree prune || true
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git branch -D "$BRANCH"
  echo "deleted branch: $BRANCH"
else
  echo "branch absent: $BRANCH"
fi

echo "cleanup done run_id=$RUN_ID"
