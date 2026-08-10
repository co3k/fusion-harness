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
    if (
        args.model is not None
        and args.model_id is not None
        and args.model != args.model_id
    ):
        print("error: --model and --model-id must match when both are set", file=sys.stderr)
        return 2
    model = args.model or args.model_id or ""
    if not model:
        print("error: --model or --model-id is required", file=sys.stderr)
        return 2
    if model == "REPLACE_ME":
        print(
            "error: model is REPLACE_ME — edit $HERMES_HOME/fusion/models.yaml before logging quality hops",
            file=sys.stderr,
        )
        return 2

    # effort: omit flag → unknown (do not pretend max was used)
    if args.effort is None or args.effort == "":
        effort = "unknown"
    else:
        effort = args.effort

    reason = args.reason if args.reason is not None else ""
    # keep reason key even when empty so contracts "every hop logs reason" holds
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id or "",
        "route": args.route,
        "model": model,
        "model_id": model,  # contracts.md field; mirror model for compatibility
        "effort": effort,
        "backend": args.backend,
        "reason": reason,
        "outcome": args.outcome,
        "objective": args.objective or "",
        "task_class": args.task_class or "",
        "tokens_in": args.tokens_in,
        "tokens_out": args.tokens_out,
        "measured_cost_usd": args.cost,
        "duration_s": args.duration_s,
        "notes": args.notes or "",
    }
    # drop nulls and empty strings except reason (always kept) and effort (always kept)
    keep_empty = {"reason", "effort"}
    rec = {
        k: v
        for k, v in rec.items()
        if v is not None and (v != "" or k in keep_empty)
    }
    path = history_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": True, "path": str(path), **rec}, ensure_ascii=False))
    return 0


def _read_all() -> tuple[list[dict], int]:
    path = history_path()
    rows: list[dict] = []
    corrupt = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            corrupt += 1
            continue
    return rows, corrupt


def cmd_summary(args: argparse.Namespace) -> int:
    all_rows, corrupt = _read_all()
    if args.last < 0:
        print("error: --last must be zero or a positive integer", file=sys.stderr)
        return 2
    rows = all_rows if args.last == 0 else all_rows[-args.last :]
    total = len(all_rows) + corrupt
    by_route: dict[str, Counter] = defaultdict(Counter)
    for r in all_rows:
        route = r.get("route", "?")
        by_route[route][r.get("outcome", "?")] += 1
    print(
        f"history_lines_total={len(all_rows)} window_lines={len(rows)} "
        f"corrupt_lines={corrupt} "
        f"scanned_nonempty={total} path={history_path()}"
    )
    print("by_route (full history):")
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
    a.add_argument(
        "--model",
        default=None,
        help="model id (alias of --model-id; required one of them)",
    )
    a.add_argument(
        "--model-id",
        default=None,
        dest="model_id",
        help="model id (contracts.md name; alias of --model)",
    )
    a.add_argument(
        "--effort",
        default=None,
        help="requested effort; if omitted logs effort=unknown (does not assume max)",
    )
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
    # Align with SKILL.md example (`--last 20`); zero explicitly means all rows.
    s.add_argument("--last", type=int, default=20, help="window size; 0 means all rows")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(func=cmd_summary)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
