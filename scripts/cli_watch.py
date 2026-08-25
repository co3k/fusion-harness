#!/usr/bin/env python3
"""Report (and optionally apply) worker-CLI updates.

Never writes models.yaml / history.jsonl. Stdlib + the host package manager
already used by each CLI (`claude update`, `codex update`, `opencode upgrade`,
`agent update`).

Subcommands are flags:
  python3 scripts/cli_watch.py              # report only
  python3 scripts/cli_watch.py --apply      # apply official updaters
  python3 scripts/cli_watch.py --quiet-if-empty
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(argv: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _parse_semver(text: str) -> str:
    m = re.search(r"(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)", text or "")
    if m:
        return m.group(1)
    m = re.search(r"(\d{4}\.\d{2}\.\d{2}-[0-9A-Za-z]+)", text or "")
    if m:
        return m.group(1)
    return (text or "").strip().split()[0] if (text or "").strip() else ""


def _npm_latest(package: str) -> str:
    npm = shutil.which("npm")
    if not npm:
        return ""
    try:
        proc = _run([npm, "view", package, "version"], timeout=45)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _version_of(argv: list[str]) -> str:
    try:
        proc = _run(argv, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _parse_semver(blob)


def _apply(argv: list[str], timeout: int = 300) -> tuple[int, str]:
    try:
        proc = _run(argv, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as exc:
        return 127, str(exc)
    blob = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    return proc.returncode, blob[-2000:]


def collect() -> list[dict]:
    rows: list[dict] = []
    if shutil.which("claude"):
        rows.append(
            {
                "name": "claude",
                "current": _version_of(["claude", "--version"]),
                "latest": _npm_latest("@anthropic-ai/claude-code"),
                "apply": ["claude", "update"],
            }
        )
    if shutil.which("codex"):
        rows.append(
            {
                "name": "codex",
                "current": _version_of(["codex", "--version"]),
                "latest": _npm_latest("@openai/codex"),
                "apply": ["codex", "update"],
            }
        )
    if shutil.which("opencode"):
        rows.append(
            {
                "name": "opencode",
                "current": _version_of(["opencode", "--version"]),
                "latest": _npm_latest("opencode-ai"),
                "apply": ["opencode", "upgrade", "--method", "npm"],
            }
        )
    cursor = shutil.which("cursor-agent") or shutil.which("agent")
    if cursor:
        rows.append(
            {
                "name": "cursor-agent",
                "current": _version_of([cursor, "--version"]),
                "latest": "",  # date-stamped; compare before/after apply
                "apply": [cursor, "update"],
            }
        )
    return rows


def stale(row: dict) -> bool:
    current, latest = row.get("current") or "", row.get("latest") or ""
    if current and latest and current != latest:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="run official updaters for stale CLIs")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet-if-empty", action="store_true")
    ap.add_argument(
        "--apply-unknown-latest",
        action="store_true",
        help="also apply CLIs whose registry latest is unknown (cursor-agent)",
    )
    args = ap.parse_args()

    rows = collect()
    changed: list[dict] = []
    for row in rows:
        row["stale"] = stale(row)
        row["applied"] = False
        row["apply_exit"] = None
        should_apply = args.apply and (
            row["stale"] or (args.apply_unknown_latest and not row.get("latest"))
        )
        if should_apply and row.get("apply"):
            before = row["current"]
            code, _out = _apply(list(row["apply"]))
            after = _version_of([row["apply"][0], "--version"])
            row["applied"] = True
            row["apply_exit"] = code
            row["after"] = after
            if after and after != before:
                changed.append(row)
            elif row["stale"] and code != 0:
                changed.append(row)
        elif row["stale"]:
            changed.append(row)

    report = {
        "generated_at": _iso(),
        "models_yaml_written": False,
        "history_written": False,
        "apply": bool(args.apply),
        "clis": [
            {
                "name": r["name"],
                "current": r.get("current"),
                "latest": r.get("latest") or None,
                "stale": r.get("stale"),
                "applied": r.get("applied"),
                "after": r.get("after"),
                "apply_exit": r.get("apply_exit"),
            }
            for r in rows
        ],
        "changed": [r["name"] for r in changed],
    }

    quiet = args.quiet_if_empty and not changed and not any(r.get("applied") for r in rows)
    if quiet:
        return 0
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    lines = [f"### Fusion CLI watch {report['generated_at'][:19]}"]
    if not rows:
        lines.append("- no worker CLIs found on PATH")
    for r in rows:
        latest = r.get("latest") or "?"
        after = r.get("after")
        mark = "STALE" if r.get("stale") else "ok"
        extra = ""
        if r.get("applied"):
            extra = f" → applied {after or '?'} (exit {r.get('apply_exit')})"
        lines.append(f"- {r['name']}: {r.get('current') or '?'} / latest {latest} [{mark}]{extra}")
    lines.append("- models.yaml: unchanged")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
