#!/usr/bin/env bash
# Local smoke tests for fusion-harness scripts (no network).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HERMES_HOME
HERMES_HOME="$(mktemp -d)"
trap 'rm -rf "$HERMES_HOME" "$REPO_PARENT" 2>/dev/null || true' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "OK: $*"; }

# --- fusion_init ---
bash "$ROOT/scripts/fusion_init.sh" >/dev/null
[[ -f "$HERMES_HOME/fusion/models.yaml" ]] || fail "models.yaml missing"
[[ -f "$HERMES_HOME/fusion/routes.yaml" ]] || fail "routes.yaml missing"
# second run leaves models
echo keep >"$HERMES_HOME/fusion/models.yaml"
bash "$ROOT/scripts/fusion_init.sh" >/dev/null
grep -q keep "$HERMES_HOME/fusion/models.yaml" || fail "init overwrote models"
pass "fusion_init"

# --- fusion_log ---
python3 -m py_compile "$ROOT/scripts/fusion_log.py"
out="$(python3 "$ROOT/scripts/fusion_log.py" append \
  --route scout --model-id test-model --backend delegate_task \
  --outcome accepted --reason "smoke" --effort medium --run-id smoke1)"
echo "$out" | grep -q '"model_id": "test-model"' || fail "model_id missing in append"
echo "$out" | grep -q '"effort": "medium"' || fail "effort not recorded"
# omit effort → unknown
out2="$(python3 "$ROOT/scripts/fusion_log.py" append \
  --route verify --model m2 --backend delegate_task --outcome accepted --reason r)"
echo "$out2" | grep -q '"effort": "unknown"' || fail "omitted effort should be unknown"
# REPLACE_ME rejected
if python3 "$ROOT/scripts/fusion_log.py" append \
  --route produce --model REPLACE_ME --backend delegate_task --outcome accepted --reason x 2>/dev/null; then
  fail "REPLACE_ME should be rejected"
fi
# corrupt line counting
printf 'not-json\n' >>"$HERMES_HOME/fusion/history.jsonl"
sum="$(python3 "$ROOT/scripts/fusion_log.py" summary --last 50)"
echo "$sum" | grep -q 'corrupt_lines=1' || fail "corrupt_lines not reported: $sum"
pass "fusion_log"

# --- probe ---
pb="$(bash "$ROOT/scripts/probe_backends.sh")"
echo "$pb" | grep -q 'delegate_task: unknown' || fail "probe should not hardcode delegate_task yes"
pass "probe_backends"

# --- worktree prepare/cleanup ---
REPO_PARENT="$(mktemp -d)"
REPO="$REPO_PARENT/demo"
git init -q "$REPO"
git -C "$REPO" config user.email smoke@test
git -C "$REPO" config user.name smoke
echo x >"$REPO/f"
git -C "$REPO" add f
git -C "$REPO" commit -qm init

# relative must fail
if bash "$ROOT/scripts/worktree_prepare.sh" ./demo bad 2>/dev/null; then
  fail "relative REPO should fail"
fi
# path traversal run_id must fail
if bash "$ROOT/scripts/worktree_prepare.sh" "$REPO" '../evil' 2>/dev/null; then
  fail "bad run_id should fail"
fi
# happy path + trailing slash
bash "$ROOT/scripts/worktree_prepare.sh" "${REPO}/" smoke-wt >/dev/null
[[ -f "$HERMES_HOME/fusion/runs/smoke-wt/worktree.txt" ]] || fail "worktree.txt missing"
WT="$(cat "$HERMES_HOME/fusion/runs/smoke-wt/worktree.txt")"
[[ "$WT" == /* ]] || fail "worktree path not absolute: $WT"
[[ -d "$WT" ]] || fail "worktree dir missing"
# nested inside repo would be wrong
case "$WT" in
  "$REPO"/*) fail "worktree nested inside repo: $WT" ;;
esac
bash "$ROOT/scripts/worktree_cleanup.sh" smoke-wt >/dev/null
[[ ! -e "$WT" ]] || fail "worktree still exists after cleanup"
pass "worktree prepare/cleanup"

echo "ALL SMOKE PASSED"
