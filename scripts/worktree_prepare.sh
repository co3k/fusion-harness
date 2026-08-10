#!/usr/bin/env bash
# Create a disposable git worktree for a fusion run.
# Usage: worktree_prepare.sh <repo_abs> <run_id>
# run_id: slug only [A-Za-z0-9._-]+  (no path separators)
# repo: must be an absolute path (trailing slashes stripped)
set -euo pipefail

REPO="${1:?repo abs path}"
RUN_ID="${2:?run_id}"

# strip trailing slashes
while [[ "$REPO" == */ ]]; do
  REPO="${REPO%/}"
done

if [[ "$REPO" != /* ]]; then
  echo "REPO must be an absolute path (got: $REPO)" >&2
  exit 1
fi
if [[ ! -d "$REPO" ]]; then
  echo "REPO is not a directory: $REPO" >&2
  exit 1
fi
if ! REPO="$(cd "$REPO" && git rev-parse --show-toplevel)"; then
  echo "not a git repo: $REPO" >&2
  exit 1
fi
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "run_id must match ^[A-Za-z0-9._-]+\$ (got: $RUN_ID)" >&2
  exit 1
fi
if [[ "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
  echo "run_id must not be . or .. (got: $RUN_ID)" >&2
  exit 1
fi

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
if [[ "$HERMES_HOME" != /* ]]; then
  echo "HERMES_HOME must be an absolute path (got: $HERMES_HOME)" >&2
  exit 1
fi
RUN_DIR="$HERMES_HOME/fusion/runs/$RUN_ID"
mkdir -p "$RUN_DIR"
RUN_DIR="$(cd "$RUN_DIR" && pwd)"

BRANCH="fusion/${RUN_ID}"
BASE_SHA="$(git -C "$REPO" rev-parse HEAD)"
# sibling directory to avoid nesting inside the repo
PARENT="$(dirname "$REPO")"
BASE="$(basename "$REPO")"
WT="${PARENT}/.fusion-wt-${BASE}-${RUN_ID}"

if [[ -e "$WT" ]]; then
  echo "worktree path exists: $WT" >&2
  exit 1
fi
if git -C "$REPO" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "branch already exists: $BRANCH (remove it or choose another run_id)" >&2
  exit 1
fi

git -C "$REPO" worktree add "$WT" -b "$BRANCH"
# always record absolute paths
echo "$WT" | tee "$RUN_DIR/worktree.txt"
echo "$BRANCH" | tee "$RUN_DIR/branch.txt"
echo "$REPO" | tee "$RUN_DIR/repo.txt"
echo "$BASE_SHA" >"$RUN_DIR/base_sha.txt"
echo "worktree_path=$WT worktree_branch=$BRANCH repo=$REPO base_sha=$BASE_SHA"
