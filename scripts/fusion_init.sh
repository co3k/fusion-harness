#!/usr/bin/env bash
# Initialize $HERMES_HOME/fusion from skill templates.
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HERMES_HOME/fusion"
mkdir -p "$DEST/runs"
if [[ ! -f "$DEST/models.yaml" ]]; then
  cp "$SKILL_DIR/references/templates/models.yaml" "$DEST/models.yaml"
  echo "created $DEST/models.yaml — edit REPLACE_ME binds before quality runs"
else
  echo "exists $DEST/models.yaml (left untouched)"
fi
if [[ ! -f "$DEST/routes.yaml" ]]; then
  cp "$SKILL_DIR/references/templates/routes.yaml" "$DEST/routes.yaml"
  echo "created $DEST/routes.yaml"
fi
touch "$DEST/history.jsonl"
echo "fusion home: $DEST"
