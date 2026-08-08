#!/usr/bin/env bash
# Print which fusion worker backends look available.
set -euo pipefail
have() { command -v "$1" >/dev/null 2>&1 && echo "yes" || echo "no"; }
echo "fusion backend probe ($(date -Iseconds 2>/dev/null || date))"
echo "HERMES_HOME=${HERMES_HOME:-$HOME/.hermes}"
echo "delegate_task: yes  # Hermes built-in (runtime)"
echo "codex:  $(have codex)"
echo "claude: $(have claude)"
echo "acpx:   $(have acpx)"
echo "git:    $(have git)"
# a2a is a Hermes toolset — cannot know from shell alone
echo "a2a:    unknown (enable hermes a2a toolset + peers)"
if command -v codex >/dev/null 2>&1; then
  echo "--- codex --version ---"
  codex --version 2>&1 | head -5 || true
fi
if command -v claude >/dev/null 2>&1; then
  echo "--- claude --version ---"
  claude --version 2>&1 | head -5 || true
fi
