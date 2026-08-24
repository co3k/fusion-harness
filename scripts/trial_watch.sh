#!/usr/bin/env bash
# Cron/watchdog entry for fusion-harness challenger trials.
# Quiet when nothing new is advertised (stdout empty → cron stays silent).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

# cron often has a bare PATH; activate mise so opencode/claude/codex resolve.
if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate bash)" 2>/dev/null || true
elif [[ -x "${HOME}/.local/bin/mise" ]]; then
  eval "$("${HOME}/.local/bin/mise" activate bash)" 2>/dev/null || true
fi

exec python3 "$ROOT/scripts/trial.py" watch --probe --auto --quiet-if-empty --max-per-run 2
