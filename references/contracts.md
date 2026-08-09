# Fusion contracts

## Handoff (`handoff-<route>.md`)

```markdown
# Handoff
- run_id: <id>
- route: scout | produce | implement | verify | review | advise | …
- objective: quality | balanced | economy
- model_id: <from models.yaml or unknown>
- effort: max | xhigh | high | medium | low   # requested; default max
- backend: delegate_task | codex | claude | acpx | a2a | terminal
- repo: <absolute path to git root>
- worktree_path: <absolute path to disposable worktree>   # prefer this
- worktree_branch: <branch name, e.g. fusion/<run_id>>   # prefer this
- worktree: <deprecated single field — absolute path preferred; do not put branch name here>
- base_ref: <main or starting sha>

## Goal
<one paragraph>

## Context
- files/dirs of interest:
- prior hops:
- user constraints:

## Constraints
- do / don't
- test command if known:
- time/budget hints:

## Working policy
- requested effort: <effort> (do not lower without lead re-bind)
- model/backend as above

## Acceptance criteria
- [ ] …
- [ ] …

## Return shape
Write `return-<route>.md` with sections: Summary, Changes, Tests, Risks, Followups.
On failure: Blocked-reason, Partial-changes, Need-from-lead.
```

## Return (`return-<route>.md`)

```markdown
# Return
- run_id:
- route:
- model_id:
- effort_requested:
- effort_resolved: <if known, else unknown>
- backend:
- outcome: accepted_candidate | needs_rework | blocked | failed

## Summary
## Changes (paths)
## Tests (commands + results)
## Risks
## Followups for lead
## Tokens / cost (if known)
```

## Compact reclassify handoff

When promoting route or changing model, new session only. Include:

- What was tried (routes/models)
- What failed (symptoms, not essays)
- Current tree state (branch, dirty paths)
- Single next goal + acceptance
