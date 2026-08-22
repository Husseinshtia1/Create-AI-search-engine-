from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict

from .server import run_server
from .service import LiveSearchService


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="g97-live", description="G97 Live Alpha crawler/search runtime")
    p.add_argument("--data-dir", default=".g97-live", help="runtime data directory")
    sub = p.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="add one URL to the durable frontier")
    submit.add_argument("url")

    crawl = sub.add_parser("crawl", help="process queued URLs")
    crawl.add_argument("--limit", type=int, default=100)
    crawl.add_argument("--max-depth", type=int, default=2)
    crawl.add_argument("--max-retries", type=int, default=2)

    worker = sub.add_parser("worker", help="continuously process the durable crawl frontier")
    worker.add_argument("--max-depth", type=int, default=2)
    worker.add_argument("--max-retries", type=int, default=2)
    worker.add_argument("--idle-sleep", type=float, default=2.0)

    search = sub.add_parser("search", help="search the local live index")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=10)

    sub.add_parser("status", help="show repository/frontier/telemetry state")

    serve = sub.add_parser("serve", help="serve the public search UI/API and URL submission endpoint")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "serve":
        run_server(args.data_dir, host=args.host, port=args.port)
        return

    service = LiveSearchService(args.data_dir)
    if args.command == "submit":
        print(json.dumps({"added": service.submit_url(args.url), "url": args.url}))
    elif args.command == "crawl":
        results = service.crawl(limit=args.limit, max_depth=args.max_depth, max_retries=args.max_retries)
        print(json.dumps([asdict(result) for result in results], default=str, ensure_ascii=False, indent=2))
    elif args.command == "worker":
        try:
            while True:
                result = service.crawl_once(max_depth=args.max_depth, max_retries=args.max_retries)
                if result is None:
                    time.sleep(max(0.1, args.idle_sleep))
                else:
                    print(json.dumps(asdict(result), default=str, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            return
    elif args.command == "search":
        print(json.dumps([asdict(hit) for hit in service.search(args.query, k=args.k)], ensure_ascii=False, indent=2))
    elif args.command == "status":
        print(json.dumps(service.status(), indent=2))


if __name__ == "__main__":
    main()
