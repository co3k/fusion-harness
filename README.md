# fusion-harness

Hermes skill for **visible multi-model orchestration**: a lead agent plans and
accepts; workers execute specialized hops. Model, backend, and effort are
explicit, logged, and user-controlled.

Inspired by hybrid lead/sidekick patterns (e.g. Devin Fusion) without locking
to a single vendor model, CLI, or personal workflow.

## Install (Hermes)

```bash
# clone into your Hermes skills tree
mkdir -p "${HERMES_HOME:-$HOME/.hermes}/skills/software-development"
git clone https://github.com/co3k/fusion-harness.git \
  "${HERMES_HOME:-$HOME/.hermes}/skills/software-development/fusion-harness"

# or copy SKILL.md + references/ + scripts/ into that path
```

Start a **new** Hermes session so the skill loader picks it up. Then ask for a
fusion-style run (multi-hop produce/implement/review with visible routing).

## One-time host setup

```bash
bash scripts/fusion_init.sh          # creates $HERMES_HOME/fusion/
bash scripts/probe_backends.sh       # shell-visible CLIs (delegate_task/a2a = unknown)
chmod +x scripts/*.sh scripts/fusion_log.py   # if your install dropped +x
$EDITOR "$HERMES_HOME/fusion/models.yaml"   # replace REPLACE_ME + set updated_at
python3 scripts/fusion_log.py append --help
bash scripts/smoke_test.sh           # optional local smoke
```

User-owned config lives under `$HERMES_HOME/fusion/` (not in this repo):

| File | Purpose |
|------|---------|
| `models.yaml` | route → model / backend / **effort** |
| `routes.yaml` | optional logical route overrides |
| `history.jsonl` | production-hop evidence |
| `advertised_seen.json` | advertised-ID snapshot (`trial.py discover`) |
| `trial_queue.json` | new IDs waiting for a shadow ping |
| `trials.jsonl` | shadow-trial evidence (never mixed into history) |
| `runs/<id>/` | handoffs and returns |

## Core ideas

| Concept | Meaning |
|---------|---------|
| Lead | Current Hermes session model — decide, contract, accept |
| Workers | Pluggable backends (`delegate_task`, Codex, Claude CLI, acpx, a2a, …) |
| Route ≠ model ≠ effort | Bind all three in `models.yaml` |
| Effort default | **max** (Codex: `xhigh`) except clearly light hops |
| Evidence | Every hop logs route/model/backend/effort/outcome |
| Challenger trial | New advertised IDs are shadow-pinged automatically; `models.yaml` stays human-gated |

Domain-agnostic: coding, research, writing, advice prep, comparisons — **no
built-in topic denylist**.

## Layout

```text
SKILL.md                 # agent procedure
references/
  contracts.md           # handoff / return shapes
  selection.md           # classify + bind
  backends.md            # CLI flags including effort
  model-candidates.md    # dated bootstrap menu (not mandatory IDs)
  templates/             # starter models.yaml / routes.yaml
scripts/
  fusion_init.sh
  fusion_log.py
  trial.py               # new-model discover + isolated shadow pings
  trial_watch.sh         # cron/watchdog entry (quiet if nothing new)
  probe_backends.sh
  worktree_prepare.sh
  worktree_cleanup.sh
  smoke_test.sh
```

## Related

- Conceptual ancestor (Claude/Fable-shaped): [co3k/fable-fusion](https://github.com/co3k/fable-fusion)
- Hermes Agent: https://hermes-agent.nousresearch.com/

## License

MIT
