#!/usr/bin/env bash
# Initialize $HERMES_HOME/fusion from skill templates.
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HERMES_HOME/fusion"
TPL_MODELS="$SKILL_DIR/references/templates/models.yaml"
TPL_ROUTES="$SKILL_DIR/references/templates/routes.yaml"

if [[ ! -f "$TPL_MODELS" ]]; then
  echo "missing template: $TPL_MODELS" >&2
  exit 1
fi
if [[ ! -f "$TPL_ROUTES" ]]; then
  echo "missing template: $TPL_ROUTES" >&2
  exit 1
fi

mkdir -p "$DEST/runs"
if [[ ! -f "$DEST/models.yaml" ]]; then
  cp "$TPL_MODELS" "$DEST/models.yaml"
  chmod 600 "$DEST/models.yaml" 2>/dev/null || true
  echo "created $DEST/models.yaml — replace REPLACE_ME binds before quality runs"
  echo "note: template updated_at=1970-01-01 is a sentinel until you set a real date"
else
  echo "exists $DEST/models.yaml (left untouched)"
fi
if [[ ! -f "$DEST/routes.yaml" ]]; then
  cp "$TPL_ROUTES" "$DEST/routes.yaml"
  chmod 600 "$DEST/routes.yaml" 2>/dev/null || true
  echo "created $DEST/routes.yaml"
fi
touch "$DEST/history.jsonl"
echo "fusion home: $DEST"
