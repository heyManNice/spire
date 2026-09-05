"""Minimal CLI: `python -m spire apps` / `python -m spire dump <app>`."""

from __future__ import annotations

import argparse
import json

from spire import tree, __version__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="spire", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("apps", help="list running applications")

    dump = sub.add_parser("dump", help="dump an application's a11y tree")
    dump.add_argument("app")
    dump.add_argument("--json", action="store_true")
    dump.add_argument("--max-depth", type=int, default=25)
    dump.add_argument("--max-nodes", type=int, default=1000)

    args = parser.parse_args(argv)
    if args.command == "apps":
        for app in tree.applications():
            print(f"{app.name}")
        return 0
    if args.command == "dump":
        app = tree.app_by_name(args.app)
        if app is None:
            parser.error(f"application {args.app!r} not found")
        if args.json:
            print(json.dumps(
                tree.snapshot(app, args.max_depth, args.max_nodes),
                ensure_ascii=False, indent=1))
        else:
            print(tree.dump_text(app, args.max_depth, args.max_nodes))
        return 0
    return 1
