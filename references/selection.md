# Route selection and model binding

## Classify (lead)

1. Pick `task_class` (examples, not a closed enum):  
   `investigate` | `produce` | `implement` | `fix` | `advise` | `compare` | `economy_produce` | …
2. Pick `objective`: `quality` | `balanced` | `economy` (user override wins)
3. Emit ordered `routes[]` from SKILL.md defaults and/or `routes.yaml`  
   Drop scout when the plan is already tight and actionable.

## Bind (per route)

Precedence:

1. User explicit model/backend/**effort** for this hop  
2. `$HERMES_HOME/fusion/models.yaml` entry for route, with objective suffixes when present:
   - `economy` → try `produce_economy` / `implement_economy` before base
   - `quality` → try `implement_quality` / `review_quality` / `advise_quality` before base
3. `models.yaml` `defaults`  
4. Same model as lead + `delegate_task` for read-only routes only  
5. Else **stop** and ask user to fill `models.yaml`

**Effort bind:** route.effort → defaults.effort → **`max`**.  
Do not infer low effort from `objective=economy` except on routes you classify as light (scout/verify mechanical).

### models.yaml shape

```yaml
updated_at: "YYYY-MM-DD"
defaults:
  backend: delegate_task
  effort: max          # default for all routes unless overridden
routes:
  scout:
    model: "<id>"
    backend: delegate_task
    effort: medium     # light hop exception
  produce:
    model: "<id>"
    backend: claude
    effort: max
  implement:
    model: "<id>"
    backend: codex
    effort: max        # maps to Codex xhigh
  review:
    model: "<id>"
    backend: claude
    effort: max
```

## History bias (optional)

If `history.jsonl` has ≥3 lines for the same route:

- Prefer binds with higher accept rate and lower rework  
- **Never** auto-edit `models.yaml`; only suggest a diff  

New advertised IDs that have never been used in production are **not**
history-bias candidates. They go through `scripts/trial.py` (isolated
shadow ping → `trials.jsonl`) first. See SKILL.md → Challenger trials.

## Diversity

- `review` should differ in provider/family from `produce`/`implement` when possible  
- `compare`: two produce binds with different families  

## Reclassify triggers

- Scout shows scope ≫ plan → split/add produce hops  
- Verify fails twice → rework produce with evidence, or promote objective  
- Review finds structural issue → lead chooses rework vs escalate  
  (lead does not silently redo the produce hop while claiming the worker did)  
