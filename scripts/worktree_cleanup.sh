#!/usr/bin/env bash
# Remove a disposable fusion worktree created by worktree_prepare.sh.
# Usage:
#   worktree_cleanup.sh <run_id>
#   worktree_cleanup.sh <repo_abs> <run_id>
# Prefers paths recorded under $HERMES_HOME/fusion/runs/<run_id>/.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
if [[ "$HERMES_HOME" != /* ]]; then
  echo "HERMES_HOME must be an absolute path (got: $HERMES_HOME)" >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  RUN_ID="$1"
  CALLER_REPO=""
elif [[ $# -eq 2 ]]; then
  CALLER_REPO="$1"
  RUN_ID="$2"
  while [[ "$CALLER_REPO" == */ ]]; do CALLER_REPO="${CALLER_REPO%/}"; done
  if [[ -n "$CALLER_REPO" && "$CALLER_REPO" != /* ]]; then
    echo "REPO must be an absolute path (got: $CALLER_REPO)" >&2
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
if [[ "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
  echo "run_id must not be . or .. (got: $RUN_ID)" >&2
  exit 1
fi

RUN_DIR="$HERMES_HOME/fusion/runs/$RUN_ID"
for marker in worktree.txt repo.txt; do
  if [[ ! -f "$RUN_DIR/$marker" ]]; then
    echo "required cleanup marker missing: $RUN_DIR/$marker" >&2
    exit 1
  fi
done

WT="$(tr -d '\r\n' <"$RUN_DIR/worktree.txt")"
RECORDED_REPO="$(tr -d '\r\n' <"$RUN_DIR/repo.txt")"
BRANCH=""
HAS_BRANCH_MARKER=0
if [[ -f "$RUN_DIR/branch.txt" ]]; then
  BRANCH="$(tr -d '\r\n' <"$RUN_DIR/branch.txt")"
  HAS_BRANCH_MARKER=1
fi

if [[ -z "$WT" || "$WT" != /* ]]; then
  echo "worktree marker must contain an absolute path: $RUN_DIR/worktree.txt" >&2
  exit 1
fi
if [[ -z "$RECORDED_REPO" || "$RECORDED_REPO" != /* ]]; then
  echo "repo marker must contain an absolute path: $RUN_DIR/repo.txt" >&2
  exit 1
fi

if ! REPO="$(cd "$RECORDED_REPO" && git rev-parse --show-toplevel)"; then
  echo "recorded repo is not a git repo: $RECORDED_REPO" >&2
  exit 1
fi
if [[ -n "$CALLER_REPO" ]]; then
  if ! CALLER_REPO="$(cd "$CALLER_REPO" && git rev-parse --show-toplevel)"; then
    echo "not a git repo: $CALLER_REPO" >&2
    exit 1
  fi
  if [[ "$CALLER_REPO" != "$REPO" ]]; then
    echo "recorded repo does not match supplied repo: $REPO != $CALLER_REPO" >&2
    exit 1
  fi
fi

cd "$REPO"

if [[ -e "$WT" ]]; then
  if [[ "${FUSION_CLEANUP_FORCE:-}" != "1" ]] && \
    [[ -n "$(git -C "$WT" status --porcelain 2>/dev/null || true)" ]]; then
    echo "refusing to remove worktree with uncommitted changes: $WT (set FUSION_CLEANUP_FORCE=1 after exporting artifacts)" >&2
    exit 1
  fi
  if ! git worktree remove "$WT"; then
    echo "normal worktree removal failed; retrying with --force: $WT" >&2
    git worktree remove --force "$WT"
  fi
  echo "removed worktree: $WT"
else
  echo "worktree path missing (already gone?): $WT"
  git worktree prune || true
fi

if [[ "$HAS_BRANCH_MARKER" -ne 1 ]]; then
  echo "branch marker missing; skipped branch deletion"
elif [[ "$BRANCH" != "fusion/${RUN_ID}" ]]; then
  echo "branch marker does not match expected fusion branch; skipped branch deletion: $BRANCH" >&2
elif git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git branch -D "$BRANCH"
  echo "deleted branch: $BRANCH"
else
  echo "branch absent: $BRANCH"
fi

echo "cleanup done run_id=$RUN_ID"
