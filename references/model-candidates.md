# Model candidate bootstrap (not mandatory IDs)

This file is a **dated menu** for operators filling `$HERMES_HOME/fusion/models.yaml`.
The skill must not treat these strings as permanently correct.

**Baseline:** 2026-08-08  
**Stale after:** 30 days — re-check vendor docs / CLI advertisements before trusting.

### Live probe notes (one ChatGPT-linked Codex + Claude Code host, 2026-08-08)

| Backend | Confirmed OK | Rejected / avoid |
|---|---|---|
| Codex `-m` | `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.5` | bare `gpt-5.6`, `o3` (400 on ChatGPT account) |
| Claude CLI `--model` | `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5`, aliases `sonnet`/`opus`/`fable`, Haiku 4.5 id | — |
| acpx Claude advertised | `default`, `sonnet`, `claude-fable-5[1m]`, `opus[1m]`, `haiku` | bare ids may warn but still forward |
| OpenCode `models` | includes luna/terra/sol, Claude 5 family, `grok-4.5`, `glm-5.2`, `kimi-k3`, … | list ≠ all tested with run |

Self-reported names inside model replies are **not** ground truth (Codex often mislabels).

## How to use

1. Probe what your backends actually accept (`codex -m`, Claude `/model`, `acpx …`, provider dashboards).
2. Copy IDs that exist for **your** account into `models.yaml`.
3. Prefer **family diversity**: produce/implement writer ≠ review family when possible.
4. Lead model = whatever Hermes is already running; do not force lead == worker.

## Role → tier (logical)

| Role | Goal | Typical tier |
|---|---|---|
| scout / verify | cheap, fast, OK with narrower judgment | economy / flash / haiku / “luna” |
| produce (general) | solid drafting & structure | mid (sonnet-class / terra-class) |
| implement (code) | agentic coding loop | mid–high coding SKU |
| implement hard | security, migrations, ambiguous design in code | high / sol-class / opus-class |
| review | independent critique | **other family** than writer |
| advise | mentoring prep, structured counsel | mid–high chat/reasoning |
| escalate orchestrator | pooled multi-agent API (optional) | user-configured only |

## Families often used in 2026-08 (examples)

Exact SKUs change; verify before bind.

### Anthropic (Claude Code / API)

| Label | Example ID | Notes |
|---|---|---|
| Fable 5 | `claude-fable-5` | Top GA-class; dual-use hardened vs Mythos |
| Opus 5 | `claude-opus-5` | High capability |
| Sonnet 5 | `claude-sonnet-5` | Default balanced |
| Haiku 4.5 | `claude-haiku-4-5-20251001` | Economy scout/verify |

Older docs may still mention Opus 4.8 — prefer **5-family** IDs when advertised.

### OpenAI (Codex)

Codex often exposes **tier nicknames** rather than raw API names:

| Tier (example) | Typical use |
|---|---|
| `gpt-5.6-luna` | scout / verify / economy implement |
| `gpt-5.6-terra` | routine implement / balanced |
| `gpt-5.6-sol` | hard implement / heavy review-from-GPT |

Confirm with your Codex build (`codex` help / model picker). Do not assume Sol/Terra/Luna remain forever.

### xAI

| Example | Notes |
|---|---|
| `grok-4.5` | Strong general; good Hermes lead / scout on xAI OAuth hosts |

### Google

| Example | Notes |
|---|---|
| `gemini-3.5-flash` | Common aux / cheap synthesize (as seen in many Hermes aux configs) |
| higher Gemini pro SKUs | bind only if your provider lists them |

### Optional pooled orchestrators

| Example | Notes |
|---|---|
| `fugu-ultra` | Multi-agent-as-model API; use as **escalate** with budget cap, not default daily lead |

### Route-exclusive / harness-specific (only if backend exists)

Examples from public routing policies (verify per install):

- Cursor `composer-2.5`
- OpenCode `glm-5.2`, `kimi-k3` (provider prefix may apply)
- Same underlying weights via different harnesses are **not** equivalent candidates

## Suggested starter binds (copy-adapt)

```yaml
updated_at: "2026-08-08"
defaults: { backend: delegate_task, effort: max }
routes:
  scout:    { model: grok-4.5, backend: delegate_task, effort: medium } # or haiku / luna
  produce:  { model: claude-sonnet-5, backend: claude }
  implement:{ model: gpt-5.6-terra, backend: codex }
  implement_quality: { model: gpt-5.6-sol, backend: codex }
  verify:   { model: grok-4.5, backend: delegate_task, effort: medium }
  review:   { model: claude-sonnet-5, backend: claude }        # after GPT writer
  advise:   { model: claude-sonnet-5, backend: claude }
escalate:
  moa: true
  external_orchestrator:
    enabled: false
    model: fugu-ultra
    budget_usd_cap: 5.0
```

After a GPT-family writer, prefer Claude (or third family) for `review`.  
After a Claude-family writer, prefer Codex GPT tier for `review`.

## Refresh checklist

- [ ] CLI/API still advertises each ID  
- [ ] Coding tiers still map to luna/terra/sol (or replacements)  
- [ ] Claude 5-family still current vs newer GA names  
- [ ] Economy candidates still meet your quality floor  
- [ ] Bump `models.yaml` `updated_at`  
