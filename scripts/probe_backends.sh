#!/usr/bin/env bash
# Print which fusion worker backends look available from the shell.
# Note: delegate_task / a2a are Hermes runtime toolsets — not fully probeable here.
set -euo pipefail
have() { command -v "$1" >/dev/null 2>&1 && echo "yes" || echo "no"; }
echo "fusion backend probe ($(date -Iseconds 2>/dev/null || date))"
echo "HERMES_HOME=${HERMES_HOME:-$HOME/.hermes}"
# Do NOT hardcode yes — shell cannot verify Hermes delegation toolset.
echo "delegate_task: unknown  # Hermes built-in when agent session has delegation; not shell-probeable"
echo "codex:  $(have codex)"
echo "claude: $(have claude)"
echo "acpx:   $(have acpx)"
echo "git:    $(have git)"
echo "a2a:    unknown  # enable hermes a2a toolset + peers; not shell-probeable"
if command -v codex >/dev/null 2>&1; then
  echo "--- codex --version ---"
  codex --version 2>&1 | head -5 || true
fi
if command -v claude >/dev/null 2>&1; then
  echo "--- claude --version ---"
  claude --version 2>&1 | head -5 || true
fi
