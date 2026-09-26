"""Command line entry point."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from crucible.model_shim import ShimConfig
from crucible.pipeline import run_pipeline
from crucible.report import render_markdown, viability
from crucible.store import Store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crucible")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run", help="harvest, build and environment-check a seed list")
    run_cmd.add_argument("seeds", type=Path)
    run_cmd.add_argument("--db", type=Path, default=Path("data/crucible.db"))
    run_cmd.add_argument("--model", default="qwen2.5-coder:7b")
    run_cmd.add_argument("--ollama", default="http://localhost:11434/v1")

    rep = sub.add_parser("report", help="print the viability report")
    rep.add_argument("--db", type=Path, default=Path("data/crucible.db"))

    args = parser.parse_args(argv)
    store = Store(args.db)
    store.init_db()

    if args.cmd == "run":
        urls = [ln.strip() for ln in args.seeds.read_text().splitlines()
                if ln.strip() and not ln.startswith("#")]
        shim = ShimConfig(base_url=args.ollama, model=args.model)
        v = asyncio.run(run_pipeline(urls, store=store, shim=shim))
        print(render_markdown(v))
        return 0

    print(render_markdown(viability(store)))
    return 0
