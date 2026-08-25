#!/usr/bin/env python3
"""New-model discovery + shadow trials for fusion-harness.

Subcommands:
  discover — advertised IDs vs binds/seen → new challengers
  run      — one isolated shadow ping/fixture
  watch    — discover + auto-run queued IDs + report (cron entry)
  report   — summarize trials.jsonl

Trials go to $HERMES_HOME/fusion/trials.jsonl, NEVER history.jsonl.
This script never writes models.yaml.

First discover with an empty seen-snapshot seeds the universe and
emits new=[] so a host with 50 advertised IDs does not fire 50 hops.
The first time a new backend appears (e.g. Cursor after OpenCode)
is also a seed — it is recorded, not flooded into the queue.
Later discovers queue only IDs that were not in that snapshot (and
are not already bound). watch pops up to --max-per-run from the queue.

Probes: `opencode models` and `cursor-agent --list-models` (empty if
unauthenticated). Deterministic, stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FIXTURE_PROMPT = "Reply with exactly: PONG and nothing else."
DEFAULT_MAX_PER_RUN = 2
DEFAULT_COOLDOWN_DAYS = 14
DEFAULT_TIMEOUT_SEC = 180


def fusion_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "fusion"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _utcnow().isoformat()


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def bare_id(value: str) -> str:
    """opencode/grok-4.6 → grok-4.6; already-bare IDs pass through."""
    value = (value or "").strip()
    if "/" in value:
        return value.split("/", 1)[1]
    return value


def parse_bound_routes(text: str) -> list[dict]:
    """Extract route/model/backend from a models.yaml-ish file. No PyYAML."""
    routes: list[dict] = []
    current: dict | None = None
    in_routes = False
    for line in text.splitlines():
        if re.match(r"^routes:\s*$", line):
            in_routes = True
            current = None
            continue
        if in_routes and re.match(r"^[A-Za-z]", line):
            in_routes = False
            current = None
            continue
        m = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if in_routes and m:
            current = {"route": m.group(1), "model": "", "backend": ""}
            routes.append(current)
            continue
        if current is None:
            continue
        mm = re.match(r"^\s+model:\s*[\"']?([^\s\"'#]+)", line)
        if mm:
            current["model"] = mm.group(1)
            continue
        bm = re.match(r"^\s+backend:\s*[\"']?([^\s\"'#]+)", line)
        if bm:
            current["backend"] = bm.group(1)
    return [r for r in routes if r["model"] and r["model"] != "REPLACE_ME"]


def parse_trial_cfg(text: str) -> dict:
    """Read the optional trial: block. Missing keys keep script defaults."""
    cfg = {
        "mode": "shadow",
        "max_per_run": DEFAULT_MAX_PER_RUN,
        "cooldown_days": DEFAULT_COOLDOWN_DAYS,
        "timeout_sec": DEFAULT_TIMEOUT_SEC,
    }
    in_trial = False
    for line in text.splitlines():
        if re.match(r"^trial:\s*$", line):
            in_trial = True
            continue
        if in_trial and re.match(r"^[A-Za-z]", line):
            break
        if not in_trial:
            continue
        m = re.match(r"^\s+mode:\s*[\"']?(off|shadow)", line, re.I)
        if m:
            cfg["mode"] = m.group(1).lower()
            continue
        m = re.match(r"^\s+max_per_run:\s*(\d+)", line)
        if m:
            cfg["max_per_run"] = int(m.group(1))
            continue
        m = re.match(r"^\s+cooldown_days:\s*(\d+)", line)
        if m:
            cfg["cooldown_days"] = int(m.group(1))
            continue
        m = re.match(r"^\s+timeout_sec:\s*(\d+)", line)
        if m:
            cfg["timeout_sec"] = int(m.group(1))
    return cfg


def load_trial_cfg() -> dict:
    path = fusion_home() / "models.yaml"
    if not path.exists():
        return parse_trial_cfg("")
    return parse_trial_cfg(path.read_text(encoding="utf-8"))


def load_bound(models_path: Path | None = None) -> list[dict]:
    path = models_path or (fusion_home() / "models.yaml")
    if not path.exists():
        return []
    return parse_bound_routes(path.read_text(encoding="utf-8"))


def bound_bare_ids(bound: list[dict]) -> set[str]:
    return {bare_id(r["model"]) for r in bound if r.get("model")}


def load_advertised(path: Path) -> list[dict]:
    raw = _read_json(path, [])
    items: list[dict] = []
    if isinstance(raw, dict) and "models" in raw:
        raw = raw["models"]
    if not isinstance(raw, list):
        return items
    for entry in raw:
        if isinstance(entry, str):
            items.append(
                {
                    "advertised_id": entry,
                    "id": bare_id(entry),
                    "backend": "unknown",
                    "source": "file",
                }
            )
            continue
        if not isinstance(entry, dict):
            continue
        advertised = str(entry.get("id") or entry.get("advertised_id") or "").strip()
        if not advertised:
            continue
        items.append(
            {
                "advertised_id": advertised,
                "id": bare_id(advertised),
                "backend": str(entry.get("backend") or "unknown"),
                "source": str(entry.get("source") or "file"),
            }
        )
    return items


def _run_capture(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def cursor_bin() -> str | None:
    return shutil.which("cursor-agent") or shutil.which("agent")


def parse_cursor_models(text: str) -> list[str]:
    """Parse `agent --list-models` / `agent models` text or JSON."""
    text = (text or "").strip()
    if not text:
        return []
    skip_ids = {"auto", "model", "models", "name", "id", "available"}

    def _keep(token: str) -> bool:
        token = (token or "").strip()
        return bool(token) and token.lower() not in skip_ids

    if text.lstrip()[:1] in "{[":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        ids: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    ids.append(item.strip())
                elif isinstance(item, dict):
                    for key in ("id", "modelId", "model", "name"):
                        if item.get(key):
                            ids.append(str(item[key]).strip())
                            break
            return list(dict.fromkeys(x for x in ids if _keep(x)))
        if isinstance(data, dict):
            for key in ("models", "data", "items"):
                if isinstance(data.get(key), list):
                    return parse_cursor_models(json.dumps(data[key]))
    ids = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.lower().startswith(("error", "tip:", "usage:")):
            continue
        if line.lower() in {"available models", "available models:"}:
            continue
        token = line.split(" - ", 1)[0].split()[0].strip(" ,;|")
        if not _keep(token):
            continue
        if re.match(r"^[A-Za-z0-9][A-Za-z0-9._:+-]*$", token):
            ids.append(token)
    return list(dict.fromkeys(ids))


def probe_opencode() -> list[dict]:
    if not shutil.which("opencode"):
        return []
    proc = _run_capture(["opencode", "models"])
    if not proc or proc.returncode != 0:
        return []
    items: list[dict] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        items.append(
            {
                "advertised_id": line,
                "id": bare_id(line),
                "backend": "opencode",
                "source": "opencode models",
            }
        )
    return items


def probe_cursor() -> list[dict]:
    exe = cursor_bin()
    if not exe:
        return []
    stdout = ""
    for argv in ([exe, "--list-models"], [exe, "models"]):
        proc = _run_capture(argv, timeout=60)
        if not proc or proc.returncode != 0:
            continue
        stdout = proc.stdout or ""
        if stdout.strip():
            break
    ids = parse_cursor_models(stdout)
    return [
        {
            "advertised_id": mid,
            "id": mid,
            "backend": "cursor",
            "source": "cursor-agent --list-models",
        }
        for mid in ids
    ]


def probe_advertised() -> list[dict]:
    return probe_opencode() + probe_cursor()


def seen_path() -> Path:
    return fusion_home() / "advertised_seen.json"


def queue_path() -> Path:
    return fusion_home() / "trial_queue.json"


def trials_path() -> Path:
    return fusion_home() / "trials.jsonl"


def infer_seeded_backends(ids: list[str]) -> list[str]:
    found: set[str] = set()
    for aid in ids:
        if aid.startswith("opencode/") or aid.startswith("opencode-go/"):
            found.add("opencode")
        elif aid.startswith("cursor/") or aid.startswith("cursor-agent/"):
            found.add("cursor")
    return sorted(found)


def load_seen() -> dict:
    data = _read_json(seen_path(), {})
    ids = data.get("ids") if isinstance(data, dict) else []
    if not isinstance(ids, list):
        ids = []
    ids = [str(x) for x in ids]
    seeded = data.get("seeded_backends") if isinstance(data, dict) else []
    if not isinstance(seeded, list) or not seeded:
        seeded = infer_seeded_backends(ids)
    return {
        "updated_at": data.get("updated_at") if isinstance(data, dict) else None,
        "ids": ids,
        "bare": {bare_id(x) for x in ids},
        "seeded_backends": [str(x) for x in seeded],
    }


def save_seen(
    advertised_ids: list[str],
    previous: list[str] | None = None,
    seeded_backends: list[str] | None = None,
) -> None:
    merged = list(dict.fromkeys((previous or []) + advertised_ids))
    payload: dict = {"updated_at": _iso(), "ids": merged}
    if seeded_backends is not None:
        payload["seeded_backends"] = sorted(set(seeded_backends))
    _write_json(seen_path(), payload)


def load_queue() -> list[dict]:
    data = _read_json(queue_path(), {})
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [x for x in items if isinstance(x, dict) and x.get("id")]


def save_queue(items: list[dict]) -> None:
    _write_json(queue_path(), {"updated_at": _iso(), "items": items})


def recently_trialed(model: str, cooldown_days: int, backend: str = "") -> bool:
    if cooldown_days <= 0:
        return False
    cutoff = _utcnow().timestamp() - cooldown_days * 86400
    target = bare_id(model)
    for row in _read_jsonl(trials_path()):
        if bare_id(str(row.get("model") or "")) != target:
            continue
        if backend and str(row.get("backend") or "") not in {"", "terminal", backend}:
            continue
        ts = str(row.get("ts") or "")
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt.timestamp() >= cutoff:
            return True
    return False


def slug(value: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return s or "model"


def classify(advertised: list[dict], bound: list[dict], seen: dict) -> dict:
    bound_ids = bound_bare_ids(bound)
    already_bound: list[dict] = []
    previously_seen: list[dict] = []
    new: list[dict] = []
    for item in advertised:
        rec = {
            "id": item["id"],
            "advertised_id": item["advertised_id"],
            "backend": item["backend"],
        }
        if item["id"] in bound_ids:
            already_bound.append(rec)
        elif item["id"] in seen["bare"]:
            previously_seen.append(rec)
        else:
            new.append(rec)
    return {
        "already_bound": already_bound,
        "previously_seen": previously_seen,
        "new": new,
    }


def cmd_discover(args: argparse.Namespace) -> int:
    if args.advertised:
        advertised = load_advertised(Path(args.advertised))
    elif args.probe:
        advertised = probe_advertised()
    else:
        print("error: pass --advertised FILE or --probe", file=sys.stderr)
        return 2

    bound = load_bound()
    seen = load_seen()
    seeded = False
    backend_seeded: list[dict] = []
    advertised_backends = {a["backend"] for a in advertised if a.get("backend")}
    known_backends = set(seen.get("seeded_backends") or [])
    if not seen["ids"]:
        # First snapshot: remember the universe, do not flood trials.
        if args.write:
            save_seen(
                [a["advertised_id"] for a in advertised],
                seeded_backends=sorted(advertised_backends),
            )
        classified = classify(advertised, bound, {"bare": {a["id"] for a in advertised}})
        classified["new"] = []
        seeded = True
    else:
        classified = classify(advertised, bound, seen)
        new_backends = advertised_backends - known_backends
        if new_backends:
            backend_seeded = [n for n in classified["new"] if n["backend"] in new_backends]
            classified["new"] = [n for n in classified["new"] if n["backend"] not in new_backends]
        if args.write:
            save_seen(
                [a["advertised_id"] for a in advertised],
                previous=seen["ids"],
                seeded_backends=sorted(known_backends | advertised_backends),
            )
            if classified["new"]:
                queue = load_queue()
                queued_keys = {(q.get("backend"), q["id"]) for q in queue}
                now = _iso()
                for item in classified["new"]:
                    key = (item["backend"], item["id"])
                    if key in queued_keys:
                        continue
                    if recently_trialed(item["id"], args.cooldown_days, item.get("backend") or ""):
                        continue
                    queue.append(
                        {
                            "id": item["id"],
                            "advertised_id": item["advertised_id"],
                            "backend": item["backend"],
                            "first_seen": now,
                        }
                    )
                    queued_keys.add(key)
                save_queue(queue)

    classified["backend_seeded"] = backend_seeded
    out = {
        "generated_at": _iso(),
        "seeded": seeded,
        "advertised": len(advertised),
        "bound_routes": [
            {"route": r["route"], "model": r["model"], "backend": r["backend"]}
            for r in bound
        ],
        **classified,
        "queue_size": len(load_queue()),
        "models_yaml_written": False,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def _default_argv(backend: str, model: str, advertised_id: str) -> list[str]:
    target = advertised_id or model
    if backend == "opencode" and shutil.which("opencode"):
        return ["opencode", "run", "-m", target, "--variant", "high", FIXTURE_PROMPT]
    if backend == "claude" and shutil.which("claude"):
        return ["claude", "-p", FIXTURE_PROMPT, "--model", model, "--output-format", "text"]
    if backend == "codex" and shutil.which("codex"):
        return [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-m",
            model,
            FIXTURE_PROMPT,
        ]
    if backend in {"cursor", "cursor-agent", "agent"}:
        exe = cursor_bin()
        if exe:
            return [
                exe,
                "-p",
                "--trust",
                "--mode",
                "ask",
                "--model",
                target,
                "--output-format",
                "text",
                FIXTURE_PROMPT,
            ]
    return []


def run_trial(
    *,
    model: str,
    backend: str,
    advertised_id: str = "",
    runner: str | None = None,
    argv: list[str] | None = None,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    notes: str = "",
) -> dict:
    trial_id = f"t{_utcnow().strftime('%Y%m%dT%H%M%SZ')}-{slug(model)}"
    tdir = fusion_home() / "trials" / trial_id
    tdir.mkdir(parents=True, exist_ok=True)
    if runner:
        cmd = shlex.split(runner)
    elif argv:
        cmd = list(argv)
    else:
        cmd = _default_argv(backend, model, advertised_id)
    if not cmd:
        rec = {
            "ts": _iso(),
            "kind": "trial",
            "phase": "ping",
            "trial_id": trial_id,
            "model": model,
            "advertised_id": advertised_id or model,
            "backend": backend,
            "outcome": "skipped",
            "notes": notes or "no runner for backend",
            "champion_untouched": True,
        }
        _append_jsonl(trials_path(), rec)
        _write_json(tdir / "meta.json", rec)
        return rec

    stdout_path = tdir / "stdout.txt"
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(tdir),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        duration = round(time.monotonic() - started, 3)
        exit_code = int(proc.returncode)
        outcome = "ok" if exit_code == 0 else "failed"
        output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    except subprocess.TimeoutExpired as exc:
        duration = round(time.monotonic() - started, 3)
        exit_code = 124
        outcome = "timeout"
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
    except OSError as exc:
        duration = round(time.monotonic() - started, 3)
        exit_code = 127
        outcome = "failed"
        output = str(exc)

    stdout_path.write_text(output, encoding="utf-8")
    rec = {
        "ts": _iso(),
        "kind": "trial",
        "phase": "ping",
        "trial_id": trial_id,
        "model": model,
        "advertised_id": advertised_id or model,
        "backend": backend,
        "outcome": outcome,
        "exit_code": exit_code,
        "duration_s": duration,
        "cmd": cmd,
        "artifact_dir": str(tdir),
        "champion_untouched": True,
        "notes": notes or "shadow ping",
    }
    _append_jsonl(trials_path(), rec)
    _write_json(tdir / "meta.json", rec)
    return rec


def cmd_run(args: argparse.Namespace) -> int:
    rec = run_trial(
        model=args.model,
        backend=args.backend,
        advertised_id=args.advertised_id or args.model,
        runner=args.runner,
        argv=list(args.cmd) if args.cmd else None,
        timeout_sec=args.timeout_sec,
        notes=args.notes,
    )
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0 if rec.get("outcome") in {"ok", "skipped"} else 1


def _pop_queue(max_n: int, cooldown_days: int) -> tuple[list[dict], list[dict]]:
    queue = load_queue()
    picked: list[dict] = []
    kept: list[dict] = []
    for item in queue:
        if len(picked) >= max_n:
            kept.append(item)
            continue
        if recently_trialed(str(item.get("id") or ""), cooldown_days, str(item.get("backend") or "")):
            continue
        picked.append(item)
    save_queue(kept)
    return picked, kept


def cmd_watch(args: argparse.Namespace) -> int:
    cfg = load_trial_cfg()
    cooldown_days = args.cooldown_days
    if args.cooldown_days == DEFAULT_COOLDOWN_DAYS:
        cooldown_days = cfg["cooldown_days"]
    timeout_sec = args.timeout_sec
    if args.timeout_sec == DEFAULT_TIMEOUT_SEC:
        timeout_sec = cfg["timeout_sec"]
    max_per_run = args.max_per_run
    if args.max_per_run == DEFAULT_MAX_PER_RUN:
        max_per_run = cfg["max_per_run"]
    auto = bool(args.auto) and cfg["mode"] != "off"

    # Discover first (may seed or enqueue).
    disc_ns = argparse.Namespace(
        advertised=args.advertised,
        probe=args.probe if not args.advertised else False,
        write=True,
        cooldown_days=cooldown_days,
    )
    if not args.advertised and not args.probe:
        # watch defaults to probing live CLIs
        disc_ns.probe = True
    # Reuse discover logic without printing.
    buf_out = sys.stdout
    from io import StringIO

    captured = StringIO()
    sys.stdout = captured
    try:
        rc = cmd_discover(disc_ns)
    finally:
        sys.stdout = buf_out
    if rc != 0:
        print(captured.getvalue(), end="")
        return rc
    discover = json.loads(captured.getvalue() or "{}")

    ran: list[dict] = []
    skipped: list[dict] = []
    if auto and not discover.get("seeded"):
        picked, remaining = _pop_queue(max_per_run, cooldown_days)
        for item in picked:
            rec = run_trial(
                model=item["id"],
                backend=item.get("backend") or "unknown",
                advertised_id=item.get("advertised_id") or item["id"],
                runner=args.runner,
                timeout_sec=timeout_sec,
                notes="watch auto shadow ping",
            )
            ran.append(rec)
        skipped = remaining
    elif discover.get("seeded"):
        skipped = []
    else:
        skipped = load_queue()

    report = {
        "generated_at": _iso(),
        "seeded": bool(discover.get("seeded")),
        "advertised": discover.get("advertised", 0),
        "new": discover.get("new", []),
        "backend_seeded": discover.get("backend_seeded", []),
        "already_bound": discover.get("already_bound", []),
        "mode": cfg["mode"],
        "auto": auto,
        "ran": [
            {
                "model": r.get("model"),
                "backend": r.get("backend"),
                "outcome": r.get("outcome"),
                "duration_s": r.get("duration_s"),
                "trial_id": r.get("trial_id"),
            }
            for r in ran
        ],
        "queue_remaining": len(skipped) if auto else len(load_queue()),
        "models_yaml_written": False,
        "history_written": False,
    }

    quiet = (
        args.quiet_if_empty
        and not report["seeded"]
        and not report["new"]
        and not report.get("backend_seeded")
        and not report["ran"]
    )
    if quiet:
        return 0
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_watch(report))
    _write_json(fusion_home() / "trials" / "last-watch.json", report)
    return 0


def _format_watch(report: dict) -> str:
    lines = [f"### Fusion trial {report['generated_at'][:19]}"]
    if report.get("seeded"):
        lines.append(
            f"- baseline seeded: {report.get('advertised', 0)} advertised IDs (no trials)"
        )
        lines.append("- next new ID will be shadow-pinged automatically")
        lines.append("- models.yaml: unchanged")
        return "\n".join(lines)
    n_new = len(report.get("new") or [])
    n_backend_seeded = len(report.get("backend_seeded") or [])
    lines.append(
        f"- advertised: {report.get('advertised', 0)} "
        f"(new: {n_new}, bound: {len(report.get('already_bound') or [])}"
        f"{f', backend_seeded: {n_backend_seeded}' if n_backend_seeded else ''})"
    )
    if report.get("ran"):
        for r in report["ran"]:
            dur = r.get("duration_s")
            dur_s = f" {dur}s" if dur is not None else ""
            lines.append(
                f"- ran: {r.get('backend')}/{r.get('model')} ping → {r.get('outcome')}{dur_s}"
            )
    else:
        lines.append("- ran: none")
    if report.get("queue_remaining"):
        lines.append(f"- queued for later: {report['queue_remaining']}")
    lines.append("- models.yaml: unchanged")
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    rows = _read_jsonl(trials_path())
    if args.last:
        rows = rows[-args.last :]
    print(f"trial_lines={len(rows)} path={trials_path()}")
    for r in rows:
        print(
            f"  {r.get('ts', '?')} {r.get('model')} {r.get('backend')} "
            f"{r.get('outcome')} {r.get('duration_s', '')}"
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    d = sp.add_parser("discover", help="diff advertised IDs against binds + seen snapshot")
    d.add_argument("--advertised", default=None, help="JSON file of advertised IDs")
    d.add_argument("--probe", action="store_true", help="probe installed CLIs (opencode models, cursor-agent --list-models)")
    d.add_argument("--write", action="store_true", help="update seen snapshot + trial queue")
    d.add_argument("--cooldown-days", type=int, default=DEFAULT_COOLDOWN_DAYS, dest="cooldown_days")
    d.set_defaults(func=cmd_discover)

    r = sp.add_parser("run", help="one isolated shadow ping (never writes models.yaml)")
    r.add_argument("--model", required=True)
    r.add_argument("--backend", required=True)
    r.add_argument("--advertised-id", default="", dest="advertised_id")
    r.add_argument("--runner", default=None, help="override command (shell-split)")
    r.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC, dest="timeout_sec")
    r.add_argument("--notes", default="")
    r.add_argument("cmd", nargs="*", help="command after -- ")
    r.set_defaults(func=cmd_run)

    w = sp.add_parser("watch", help="discover + optional auto shadow pings + report")
    w.add_argument("--advertised", default=None)
    w.add_argument("--probe", action="store_true")
    w.add_argument("--auto", action="store_true", help="run queued shadow pings")
    w.add_argument("--runner", default=None, help="override ping command for every trial")
    w.add_argument("--max-per-run", type=int, default=DEFAULT_MAX_PER_RUN, dest="max_per_run")
    w.add_argument("--cooldown-days", type=int, default=DEFAULT_COOLDOWN_DAYS, dest="cooldown_days")
    w.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC, dest="timeout_sec")
    w.add_argument("--json", action="store_true")
    w.add_argument("--quiet-if-empty", action="store_true", dest="quiet_if_empty")
    w.set_defaults(func=cmd_watch)

    p = sp.add_parser("report", help="summarize trials.jsonl")
    p.add_argument("--last", type=int, default=20)
    p.set_defaults(func=cmd_report)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
