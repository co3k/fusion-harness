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
[[ "$(stat -c '%a' "$HERMES_HOME/fusion/history.jsonl")" == "600" ]] || fail "history.jsonl is not private"
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
# empty effort is also unknown
out3="$(python3 "$ROOT/scripts/fusion_log.py" append \
  --route scout --model m3 --backend delegate_task --outcome accepted --reason r --effort '')"
echo "$out3" | grep -q '"effort": "unknown"' || fail "empty effort should be unknown"
# differing aliases must not silently pick one model
if python3 "$ROOT/scripts/fusion_log.py" append \
  --route produce --model m1 --model-id m2 --backend delegate_task --outcome accepted --reason x 2>/dev/null; then
  fail "conflicting model aliases should be rejected"
fi
# REPLACE_ME rejected
if python3 "$ROOT/scripts/fusion_log.py" append \
  --route produce --model REPLACE_ME --backend delegate_task --outcome accepted --reason x 2>/dev/null; then
  fail "REPLACE_ME should be rejected"
fi
# corrupt line counting
printf 'not-json\n' >>"$HERMES_HOME/fusion/history.jsonl"
sum="$(python3 "$ROOT/scripts/fusion_log.py" summary --last 50)"
echo "$sum" | grep -q 'corrupt_lines=1' || fail "corrupt_lines not reported: $sum"
echo "$sum" | grep -q 'history_lines_total=3' || fail "total history count not reported: $sum"
echo "$sum" | grep -q 'window_lines=3' || fail "window count not reported: $sum"
window_sum="$(python3 "$ROOT/scripts/fusion_log.py" summary --last 1)"
echo "$window_sum" | grep -q 'history_lines_total=3' || fail "full history lost outside window: $window_sum"
echo "$window_sum" | grep -q 'window_lines=1' || fail "window was not applied: $window_sum"
if python3 "$ROOT/scripts/fusion_log.py" summary --last -1 2>/dev/null; then
  fail "negative --last should be rejected"
fi
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
mkdir -p "$REPO/subdir"

# relative must fail
if bash "$ROOT/scripts/worktree_prepare.sh" ./demo bad 2>/dev/null; then
  fail "relative REPO should fail"
fi
# path traversal run_id must fail
if bash "$ROOT/scripts/worktree_prepare.sh" "$REPO" '../evil' 2>/dev/null; then
  fail "bad run_id should fail"
fi
if bash "$ROOT/scripts/worktree_prepare.sh" "$REPO" . 2>/dev/null; then
  fail "dot run_id should fail"
fi
# HERMES_HOME must be absolute and must fail before branch/worktree creation.
if HERMES_HOME=relative bash "$ROOT/scripts/worktree_prepare.sh" "$REPO" relative-home 2>/dev/null; then
  fail "relative HERMES_HOME should fail"
fi
if git -C "$REPO" show-ref --verify --quiet refs/heads/fusion/relative-home; then
  fail "relative HERMES_HOME left an orphan branch"
fi
# Cleanup must require markers and must not guess a branch name.
git -C "$REPO" branch random-branch
if bash "$ROOT/scripts/worktree_cleanup.sh" no-markers 2>/dev/null; then
  fail "cleanup without markers should fail"
fi
git -C "$REPO" show-ref --verify --quiet refs/heads/random-branch || fail "cleanup without markers deleted a branch"
# happy path + trailing slash
bash "$ROOT/scripts/worktree_prepare.sh" "${REPO}/subdir/" smoke-wt >/dev/null
[[ -f "$HERMES_HOME/fusion/runs/smoke-wt/worktree.txt" ]] || fail "worktree.txt missing"
WT="$(cat "$HERMES_HOME/fusion/runs/smoke-wt/worktree.txt")"
[[ "$WT" == /* ]] || fail "worktree path not absolute: $WT"
[[ -d "$WT" ]] || fail "worktree dir missing"
[[ "$(cat "$HERMES_HOME/fusion/runs/smoke-wt/repo.txt")" == "$REPO" ]] || fail "repo marker was not canonicalized"
# nested inside repo would be wrong
case "$WT" in
  "$REPO"/*) fail "worktree nested inside repo: $WT" ;;
esac
bash "$ROOT/scripts/worktree_cleanup.sh" smoke-wt >/dev/null
[[ ! -e "$WT" ]] || fail "worktree still exists after cleanup"
if git -C "$REPO" show-ref --verify --quiet refs/heads/fusion/smoke-wt; then
  fail "fusion branch still exists after cleanup"
fi
# A tampered branch marker must not delete an unrelated branch.
bash "$ROOT/scripts/worktree_prepare.sh" "$REPO" tampered-branch >/dev/null
TAMPERED_WT="$(cat "$HERMES_HOME/fusion/runs/tampered-branch/worktree.txt")"
git -C "$REPO" branch evil
printf 'evil\n' >"$HERMES_HOME/fusion/runs/tampered-branch/branch.txt"
bash "$ROOT/scripts/worktree_cleanup.sh" tampered-branch >/dev/null
[[ ! -e "$TAMPERED_WT" ]] || fail "tampered worktree still exists after cleanup"
git -C "$REPO" show-ref --verify --quiet refs/heads/evil || fail "tampered marker deleted evil branch"
pass "worktree prepare/cleanup"

echo "ALL SMOKE PASSED"
