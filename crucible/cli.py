"""Command line entry point.

`main` returns an exit code for every path it can reach. A traceback out of here
is a broken contract, not an error message: the caller is a shell, and a batch
that dies on an unreadable seed file should say which file and stop cleanly.
"""
from __future__ import annotations

import argparse
import json
import asyncio
from pathlib import Path

from crucible.harvest import Seed, parse_seed_file
from crucible.model_shim import ShimConfig
from crucible.pipeline import run_pipeline
from crucible.press import generate as generate_paper
from crucible.publish import publish_dataset
from crucible.research import research_pass
from crucible.report import render_markdown, viability
from crucible.store import Store


def _read_seeds(path: Path) -> list[Seed] | None:
    """Seeds from a file, or None with a message printed if it cannot be read."""
    try:
        text = path.read_text()
    except FileNotFoundError:
        print(f"crucible: no seed file at {path}")
        return None
    except OSError as exc:
        print(f"crucible: could not read seed file {path}: {exc}")
        return None
    return parse_seed_file(text)


def build_parser() -> argparse.ArgumentParser:
    """The parser, built separately so it can be checked without running it.

    The launchd job's arguments are generated in one place and parsed in
    another, and for a day the two disagreed: the job passed three flags this
    parser does not take, so every run it attempted died on an argument error
    before doing any work. A test now parses the generated argv with this
    exact parser rather than a copy, because a copy drifts the same way.
    """
    parser = argparse.ArgumentParser(prog="crucible")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run", help="harvest, build and environment-check a seed list")
    run_cmd.add_argument("seeds", type=Path)
    run_cmd.add_argument("--db", type=Path, default=Path("runs/arena.db"))
    run_cmd.add_argument("--model", default="qwen2.5-coder:7b")
    run_cmd.add_argument("--ollama", default="http://localhost:11434/v1")

    rep = sub.add_parser("report", help="print the viability report")
    rep.add_argument("--db", type=Path, default=Path("runs/arena.db"))

    paper = sub.add_parser("paper", help="generate the viability paper from run records")
    paper.add_argument("--db", type=Path, default=Path("runs/arena.db"))
    paper.add_argument("--out", type=Path, default=None)

    res = sub.add_parser("research", help="one unattended pass as defined by research.yaml")
    res.add_argument("--no-push", action="store_true")

    sched = sub.add_parser("schedule", help="install a launchd job that runs research at the cadence in research.yaml")
    sched.add_argument("--remove", action="store_true")

    params_cmd = sub.add_parser("params", help="print the research parameters as they will be used")

    sub.add_parser("schedule-status",
                   help="what launchd actually knows about the research job")

    aud = sub.add_parser("audit", help="cross-check every verdict against its transcript; prints flags, changes nothing")
    aud.add_argument("--db", type=Path, default=Path("runs/arena.db"))
    aud.add_argument("--since", default=None, help="ISO timestamp; audit rows recorded at or after it")
    aud.add_argument("--last-pass", action="store_true", help="audit only the most recent research pass")

    pub = sub.add_parser("publish", help="export the store as static JSON for the site")
    pub.add_argument("--db", type=Path, default=Path("runs/arena.db"))
    pub.add_argument("--out", type=Path, default=Path("site/public/data"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "run":
        seeds = _read_seeds(args.seeds)
        if seeds is None:
            return 2
        store = Store(args.db)
        store.init_db()
        shim = ShimConfig(base_url=args.ollama, model=args.model)
        v = asyncio.run(run_pipeline(seeds, store=store, shim=shim))
        print(render_markdown(v))
        return 0

    if args.cmd == "research":
        entry = research_pass(repo=Path.cwd(), push=not args.no_push)
        print(json.dumps(entry, indent=2))
        return 0

    if args.cmd == "schedule":
        from crucible.params import load_params
        from crucible.schedule import install, remove
        p = load_params(Path.cwd())
        print(remove() if args.remove else install(every_hours=p.cadence_hours))
        return 0

    if args.cmd == "schedule-status":
        from crucible.schedule import status
        from crucible.params import load_params
        try:
            hours = load_params(Path.cwd()).cadence_hours
        except Exception:  # noqa: BLE001
            hours = None
        print(status(every_hours=hours))
        return 0

    if args.cmd == "audit":
        from crucible.audit import audit_rows, render
        since = args.since
        if args.last_pass:
            log = Path("runs/research-passes.jsonl")
            if log.exists():
                since = json.loads(log.read_text().splitlines()[-1])["started"]
        store = Store(args.db); store.init_db()
        total, flags = audit_rows(store, since=since)
        print(render(total, flags))
        return 1 if flags else 0

    if args.cmd == "params":
        from crucible.params import load_params
        print(json.dumps(load_params(Path.cwd()).as_dict(), indent=2))
        return 0

    if args.cmd == "paper":
        store = Store(args.db)
        store.init_db()
        document = generate_paper(store)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(document)
            print(f"{args.out}  {args.out.stat().st_size} bytes")
        else:
            print(document)
        return 0

    if args.cmd == "publish":
        store = Store(args.db)
        store.init_db()
        result = publish_dataset(store, args.out)
        for path in result.files:
            print(f"{path}  {path.stat().st_size} bytes")
        return 0

    store = Store(args.db)
    store.init_db()
    print(render_markdown(viability(store)))
    return 0
