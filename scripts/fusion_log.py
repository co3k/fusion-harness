#!/usr/bin/env python3
"""Append / summarize fusion-harness history.jsonl."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def fusion_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "fusion"


def history_path() -> Path:
    p = fusion_home() / "history.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.touch()
    return p


def cmd_append(args: argparse.Namespace) -> int:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id or "",
        "route": args.route,
        "model": args.model,
        "effort": args.effort or "",
        "backend": args.backend,
        "reason": args.reason or "",
        "outcome": args.outcome,
        "objective": args.objective or "",
        "task_class": args.task_class or "",
        "tokens_in": args.tokens_in,
        "tokens_out": args.tokens_out,
        "measured_cost_usd": args.cost,
        "duration_s": args.duration_s,
        "notes": args.notes or "",
    }
    # drop nulls
    rec = {k: v for k, v in rec.items() if v is not None and v != ""}
    path = history_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": True, "path": str(path), **rec}, ensure_ascii=False))
    return 0


def _read_all() -> list[dict]:
    path = history_path()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cmd_summary(args: argparse.Namespace) -> int:
    rows = _read_all()
    if args.last:
        rows = rows[-args.last :]
    by_route: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        route = r.get("route", "?")
        by_route[route][r.get("outcome", "?")] += 1
    print(f"history_lines={len(rows)} path={history_path()}")
    for route, ctr in sorted(by_route.items()):
        print(f"  {route}: {dict(ctr)}")
    if args.verbose:
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("append", help="append one hop")
    a.add_argument("--route", required=True)
    a.add_argument("--model", required=True)
    a.add_argument("--effort", default="max")
    a.add_argument("--backend", required=True)
    a.add_argument("--outcome", required=True)
    a.add_argument("--reason", default="")
    a.add_argument("--run-id", default="")
    a.add_argument("--objective", default="")
    a.add_argument("--task-class", default="")
    a.add_argument("--tokens-in", type=int, default=None)
    a.add_argument("--tokens-out", type=int, default=None)
    a.add_argument("--cost", type=float, default=None)
    a.add_argument("--duration-s", type=float, default=None)
    a.add_argument("--notes", default="")
    a.set_defaults(func=cmd_append)

    s = sp.add_parser("summary", help="summarize history")
    s.add_argument("--last", type=int, default=50)
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(func=cmd_summary)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
