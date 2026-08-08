---
name: fusion-harness
description: "Use when multi-model fusion (lead/workers, visible routing)."
version: 1.2.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [fusion, multi-model, routing, harness, orchestration]
    related_skills: [subagent-driven-development, plan]
---

# Fusion Harness (Hermes-native)

## Overview

**Visible multi-model orchestration**: a lead agent plans and accepts; workers
execute specialized hops. Model choice is explicit, logged, and user-controlled.

Inspired by hybrid lead/sidekick patterns (e.g. Devin Fusion) and evidence-based
route binding — **not** tied to any single vendor model, CLI, or personal workflow.

- **Lead** = current Hermes session model. Lead **decides, contracts, accepts**.
  Lead does not silently do the worker's job (see Operating contract).
- **Workers** = pluggable backends (`delegate_task`, coding CLIs, `acpx`, `a2a`,
  terminal templates, …). Select by **probe + needs**, not brand defaults baked
  into this skill.
- **Route ≠ model ≠ effort**. Logical routes bind to `model_id` + `backend` +
  **`effort`** via user-owned config under `$HERMES_HOME/fusion/`.
- **Evidence over vibes**: every hop logs route/model/backend/**effort**/reason; history
  feeds later table updates (**human-approved only**).

Domain-agnostic: coding, research, writing, mentoring preparation, reviews,
comparisons, ops runbooks — any multi-step work that benefits from split roles
and explicit model routing. **No built-in topic denylist.**

## When to Use

- User wants multi-model / fusion-style execution with **visible** routing
- Work benefits from scout → produce → verify → review (or a subset)
- Cost/quality tradeoffs (`quality` / `balanced` / `economy`) matter
- Preference against opaque orchestrators as the default path

**Skip when:** a single-shot reply with the current model is enough and the
user did not ask for fusion. (That is proportionality — not a domain ban.)

## Paths (profile-safe)

```text
$HERMES_HOME/fusion/          # default: ~/.hermes/fusion/
  models.yaml                 # USER owns — frontier follow lives here
  routes.yaml                 # optional logical-route overrides
  backends.yaml               # optional probe cache / custom commands
  history.jsonl               # append-only evidence
  runs/<run_id>/              # handoffs, returns, optional workspace pointer
```

If `fusion/` is missing, run `scripts/fusion_init.sh`.

Do not hardcode machine-specific paths, org names, or private report URLs in
this skill body.

## Operating contract

1. **Lead vs worker separation**  
   - Lead: classify, bind, write contracts, gate acceptance, escalate, report.  
   - Workers: produce artifacts (code, prose, analysis, plans, etc.).  
   - Lead may do lightweight coordination I/O under `$HERMES_HOME/fusion/` only.  
   - If the hop's job is to mutate a project workspace, **lead does not** make
     those mutations while a worker backend is available.

2. **Single-writer** for a given mutable workspace (serialize or isolate).

3. **Isolation when mutating repos** — disposable worktree/branch when the
   task is git-backed implementation. Non-git tasks: use `runs/<id>/` artifacts
   only; worktree step is **optional**.

4. **Handoff is a contract** — `references/contracts.md`.

5. **Model change ⇒ new worker session** + compact handoff (no silent swap).

6. **Every hop reports**: `route`, `model_id`, `backend`, `effort`, `reason`,
   `outcome`, and cost/tokens when available.

7. **Fail visible**: unknown model → `unknown`; missing backend → say so.

## Quick loop

```text
1. Intent     → task_class + objective (quality|balanced|economy)
2. Ensure cfg → $HERMES_HOME/fusion/models.yaml
3. Classify   → ordered routes
4. Bind       → models.yaml (+ history bias optional)
5. Workspace  → worktree if git mutation; else runs/<id>/ only
6. Handoff    → runs/<id>/handoff-<route>.md
7. Worker     → backend from bind
8. Return     → runs/<id>/return-<route>.md
9. Lead gate  → accept | rework | reclassify | escalate
10. Log       → scripts/fusion_log.py append
11. Report    → user-visible hop table
```

**Done when:** acceptance criteria met, history written, user received
route/model/backend summary — or explicit block/escalate with reason.

## Task class → routes

Logical names are **roles**, not “code only”:

| task_class | Default pipeline | Typical outputs |
|---|---|---|
| `investigate` | scout → (optional) synthesize | notes, findings |
| `produce` | scout? → produce → verify? → review? | code, doc, plan, draft |
| `implement` | alias of `produce` for software | code + tests |
| `fix` | scout → produce → verify | patched artifact + checks |
| `advise` | scout → produce → review | structured advice / feedback |
| `compare` | produce×N (diverse binds) → review | decision memo |
| `economy_produce` | produce(economy) → verify? | cheaper path |

`implement` / `fix` remain valid names for coding-heavy work; they are not
the only allowed classes. Extend via `routes.yaml` + `models.yaml` without
editing this skill.

Skip scout when the user already supplied a tight, actionable plan.

## Objectives

| objective | Bias |
|---|---|
| `quality` | Stronger bind, extra review, deliberation OK; effort stays max |
| `balanced` | Default models; **effort still max** unless route is light |
| `economy` | Cheaper **model** bind; effort may drop only on scout/verify/light hops |

## Effort (first-class, with model)

**Policy default: max effort** on almost every hop. Cost control prefers
**cheaper models / fewer hops**, not quietly lowering reasoning effort on hard work.

| Band | When | Typical values |
|---|---|---|
| `max` (default) | produce, implement, review, advise, fix, compare, any judgment-heavy hop | Claude: `max` (or highest advertised). Codex: `xhigh` (or host max). |
| `high` | optional step-down only if user asks or budget hard-cap | `high` / `xhigh` |
| `low`–`medium` | **only** clearly light hops: trivial scout skim, pure log grep verify, mechanical checklist | `low` / `medium` |

Rules:

1. Bind `effort` from `models.yaml` per route; if omitted → **`defaults.effort`** → if omitted → **`max`** (map to backend vocabulary in `backends.md`).
2. `objective=economy` does **not** by itself lower effort on produce/implement/review/advise.
3. Never silent mid-session effort swap; change effort ⇒ new worker session + compact handoff (same as model change).
4. Log the **requested** effort and, if visible, the **resolved** effort.
5. Backend vocabulary differs — translate, do not invent unsupported levels.

See `references/backends.md` for CLI flags (`claude --effort`, Codex
`model_reasoning_effort`, acpx model suffixes / set options).

## Binding models and effort

1. Read `$HERMES_HOME/fusion/models.yaml`.
2. If missing, run `fusion_init.sh`; ask user to set binds before quality runs.
3. **Never** bake mandatory vendor flagship model IDs into this SKILL.
4. If `updated_at` is older than 30 days, warn once; propose revisions only
   with user approval.
5. After **10** history lines for a route, offer a table revision (diff only).

See `references/selection.md`.
Dated example menus (not mandatory IDs): `references/model-candidates.md`.

When `objective=quality` and the task is high-blast coding, prefer
`implement_quality` / `review_quality` keys in `models.yaml` if present.

## Backends (pluggable)

Probe: `scripts/probe_backends.sh`. Use first backend that satisfies route
`needs` and is installed — order is a **default preference**, overridable in
`models.yaml` / `backends.yaml`:

| Backend | Typical role |
|---|---|
| `delegate_task` | in-Hermes worker; scout/verify/synthesize |
| `codex` / `claude` / other CLIs | external agent runtimes if present |
| `acpx` | ACP bridge if present |
| `a2a` | protocol peers if toolset enabled |
| `terminal` | user-defined command template |

Coding CLIs are **examples**, not requirements. A research-only host may use
only `delegate_task` + `a2a`.

If no backend can perform a **required write/produce** hop, stop and tell the
user — do not silently collapse into unlogged lead-only work while claiming
fusion.

See `references/backends.md`.

## Escalation

1. Rework same route (tighter handoff) — max 2  
2. Reclassify / promote objective  
3. Deliberation (second worker, different model family when possible)  
4. `moa` — multi-sample / MoA if the host configures it  
5. `external_orchestrator` — optional user-configured strong orchestrator
   (e.g. a pooled multi-agent API) with **budget cap** + log  
6. `ask_user`

Do not special-case product names as mandatory escalate targets in the skill
core; put them in `models.yaml` → `escalate:`.

## Report format (to user)

```markdown
### Fusion run <id>
- objective: … | task_class: …
| hop | route | model | effort | backend | reason | outcome | cost |
- result: accepted | blocked | escalated
- artifacts: paths / branch / links
```

## Scripts

Paths are relative to this skill directory (resolve via `skill_view` / install
location; do not assume a single user's home layout beyond `$HERMES_HOME`):

```bash
bash scripts/probe_backends.sh
bash scripts/fusion_init.sh
python3 scripts/fusion_log.py summary --last 20
```

## Common Pitfalls

1. Lead does the worker's produce step while a worker backend exists — breaks
   the contract and hides cost.
2. Treating one CLI (or acpx) as mandatory — probe and configure instead.
3. Shipping model/effort only inside SKILL.md — use `models.yaml`.
4. Silent mid-session model **or effort** swap — new session + compact handoff.
5. Dropping effort to "save money" on non-light hops — prefer cheaper model or fewer hops instead.
6. Skipping history lines — evidence base never learns.
7. Parallel writers on one mutable workspace — serialize or isolate.

## Verification Checklist

- [ ] `models.yaml` present (or explicit economy/fallback path agreed)
- [ ] Lead/worker separation held for produce hops
- [ ] Each hop has handoff + return (or equivalent structured record)
- [ ] `history.jsonl` appended
- [ ] User saw route/model/backend table
- [ ] Workspace isolation cleaned up or handed off (if used)
- [ ] Escalations logged with budget when applicable

## References

- `references/contracts.md` — handoff/return shapes  
- `references/selection.md` — classify/bind  
- `references/backends.md` — worker invocation  
- `references/templates/` — starter `models.yaml` / `routes.yaml`  
