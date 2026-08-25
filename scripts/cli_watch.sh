#!/usr/bin/env bash
# Cron entry: report (and apply patch) worker CLI updates. Quiet when current.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
export PATH="${HOME}/.local/bin:${PATH}"

if command -v mise >/dev/null 2>&1; then
  eval "$(mise activate bash)" 2>/dev/null || true
elif [[ -x "${HOME}/.local/bin/mise" ]]; then
  eval "$("${HOME}/.local/bin/mise" activate bash)" 2>/dev/null || true
fi

# Default: apply only when a registry latest is known and differs (claude/codex/opencode).
# cursor-agent is date-stamped; leave it to --apply-unknown-latest on an explicit run.
exec python3 "$ROOT/scripts/cli_watch.py" --apply --quiet-if-empty
