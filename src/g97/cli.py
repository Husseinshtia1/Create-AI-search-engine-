from __future__ import annotations

import argparse
import json
from pathlib import Path

from .controller import FrozenController


def main() -> None:
    p = argparse.ArgumentParser(prog="g97", description="G97 Search research utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("controller-score", help="Score one frozen intervention-controller feature vector")
    c.add_argument("--controller", required=True)
    c.add_argument("features", nargs="+", type=float)

    a = sub.add_parser("show-controller", help="Print a frozen controller JSON")
    a.add_argument("--controller", required=True)

    args = p.parse_args()

    if args.cmd == "controller-score":
        ctrl = FrozenController.from_json(args.controller)
        score = ctrl.score(args.features)
        print(json.dumps({"score": score, "threshold": ctrl.threshold_tau, "intervene": score >= ctrl.threshold_tau}, indent=2))
    elif args.cmd == "show-controller":
        print(Path(args.controller).read_text())


if __name__ == "__main__":
    main()
