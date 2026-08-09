# Worker backends

Lead invokes **one** backend per hop. Capture stdout/stderr under `runs/<run_id>/`.

Always pass the bound **model** and **effort** (see SKILL effort policy). Translate
logical effort into backend vocabulary:

| Logical (models.yaml) | Claude CLI `--effort` | Codex `model_reasoning_effort` | Notes |
|---|---|---|---|
| `max` | `max` | `xhigh` (Codex max on this generation) | **Default for non-light hops** |
| `xhigh` | `xhigh` | `xhigh` | |
| `high` | `high` | `high` | |
| `medium` | `medium` | `medium` | light hops only by policy |
| `low` | `low` | `low` | light hops only |

If a backend lacks a level, use the nearest **higher** supported level (never silently drop below request without logging).

## delegate_task

- Use for: scout, verify, synthesize, advise drafts when no external CLI needed
- Pass handoff in `goal`/`context`
- Request return markdown per `contracts.md`
- Set child model via Hermes delegation config when available; pass effort in the handoff **Working policy** line if the child runtime honors it
- Log effort even when the child inherits the parent model

## codex

```bash
codex exec --skip-git-repo-check \
  -m "{{model}}" \
  -c "model_reasoning_effort=\"{{codex_effort}}\"" \
  --sandbox workspace-write \
  "$(cat handoff.md)"
```

- Map logical `max` → `xhigh` unless config proves a higher knobs exists
- cwd = worktree when mutating git
- Host default `~/.codex/config.toml` may already set `model_reasoning_effort`; **still pass hop effort explicitly** so fusion overrides sticky defaults

## claude CLI

```bash
claude -p "$(cat handoff.md)" \
  --model "{{model}}" \
  --effort "{{claude_effort}}" \
  --output-format text
```

- Levels observed: `low`, `medium`, `high`, `xhigh`, `max`
- Prefer full model ids for CLI; aliases (`sonnet`, `fable`) OK if verified

## acpx (optional)

```bash
acpx --model "{{model}}" --format text --approve-all \
  --non-interactive-permissions deny \
  claude exec "$(cat handoff.md)"
```

- Some agents accept effort via advertised config options (`effort`) or model id suffixes — probe `session/new` / `set`
- Prefer ACP-advertised model values when using acpx Claude (`sonnet`, `opus[1m]`, `claude-fable-5[1m]`, …)
- After session create, set effort if the agent exposes it:  
  `acpx claude set effort max` (ids vary — verify before relying)

## a2a (optional)

- Peer URL + agent name as model surrogate; include requested effort in the A2A message metadata/body if the peer supports it

## terminal template

```yaml
custom_impl:
  command: "my-agent --model {{model}} --effort {{effort}} --prompt-file {{handoff}}"
```

## Worktree (optional — git mutation tasks only)

Non-git work: skip; artifacts under `runs/<run_id>/` only.

Prefer the skill scripts (path convention must match):

```bash
# sibling of the repo: $(dirname REPO)/.fusion-wt-$(basename REPO)-<run_id>
# branch: fusion/<run_id>
# REPO must be absolute; run_id slug: [A-Za-z0-9._-]+
bash scripts/worktree_prepare.sh /abs/path/to/repo <run_id>
# … worker mutates inside worktree …
bash scripts/worktree_cleanup.sh /abs/path/to/repo <run_id>
# or, after prepare wrote repo.txt:
bash scripts/worktree_cleanup.sh <run_id>
```

Manual equivalent (same naming as `worktree_prepare.sh`):

```bash
REPO=/abs/path/to/repo
RUN_ID=my-run
PARENT="$(dirname "$REPO")"
BASE="$(basename "$REPO")"
git -C "$REPO" worktree add \
  "${PARENT}/.fusion-wt-${BASE}-${RUN_ID}" \
  -b "fusion/${RUN_ID}"
```
