from __future__ import annotations

import argparse
import json
from collections.abc import Callable

from cargo_loading.profile_solver import solve_profile_file
from cargo_loading.web_server import run_server


def main(argv: list[str] | None = None, server_runner: Callable[..., None] = run_server) -> int:
    parser = argparse.ArgumentParser(description="Pack boxes into a single ULD with a y-z cross-section profile.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    pack_parser = subparsers.add_parser("pack-profile", help="solve a single ULD profile packing problem")
    pack_parser.add_argument("--input", required=True, help="path to profile packing input JSON")
    pack_parser.add_argument("--output", required=True, help="directory for packing_result.json")
    serve_parser = subparsers.add_parser("serve-profile", help="run the browser visualizer")
    serve_parser.add_argument("--host", default="127.0.0.1", help="web server host")
    serve_parser.add_argument("--port", type=int, default=8000, help="web server port")
    serve_parser.add_argument("--static-dir", default="web", help="directory containing index.html, styles.css and app.js")

    args = parser.parse_args(argv)
    if args.command == "pack-profile":
        result = solve_profile_file(args.input, args.output)
        print(
            json.dumps(
                {
                    "loaded_count": result.loaded_count,
                    "unloaded_count": result.unloaded_count,
                    "volume_utilization": result.volume_utilization,
                    "validation_passed": result.validation_passed,
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "serve-profile":
        server_runner(host=args.host, port=args.port, static_dir=args.static_dir)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
