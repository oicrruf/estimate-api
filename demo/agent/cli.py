"""CLI pública y determinista de la vertical sintética AT-227."""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from relate import RelateError

from demo.agent.agent import EvaluationRequest, evaluate_offline
from demo.agent.graph import seed_store


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m demo.agent.cli",
        description=(
            "Demo local ADK + Relate con datos y precios ficticios; sin LLM ni credenciales."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("seed", "evaluate", "demo"):
        command = commands.add_parser(name)
        command.add_argument(
            "--store", type=Path, required=True, help="Ruta local explícita del archivo .rl"
        )
        if name == "evaluate":
            command.add_argument("--scenario", choices=("switch", "camera", "ups"), required=True)
            command.add_argument("--poe-ports-min", type=int, help="Mínimo PoE de switch: 1..16")
            command.add_argument("--quantity", type=int, help="Cantidad de cámaras: 1..16")
    return parser


def _request(args: argparse.Namespace) -> EvaluationRequest:
    if args.scenario != "switch" and args.poe_ports_min is not None:
        raise ValueError("--poe-ports-min sólo corresponde a switch")
    if args.scenario != "camera" and args.quantity is not None:
        raise ValueError("--quantity sólo corresponde a camera")
    return EvaluationRequest(
        scenario=args.scenario,
        poe_ports_min=args.poe_ports_min if args.poe_ports_min is not None else 8,
        quantity=args.quantity if args.quantity is not None else 4,
    )


def _evaluate_subprocess(store: Path, scenario: str, *options: str) -> dict[str, Any]:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "demo.agent.cli",
            "evaluate",
            "--store",
            str(store),
            "--scenario",
            scenario,
            *options,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return cast(dict[str, Any], json.loads(process.stdout))


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    store = args.store.resolve()
    try:
        if args.command == "seed":
            output = {"storePath": str(store), **seed_store(store)}
        elif args.command == "evaluate":
            request = _request(args)
            output = asyncio.run(evaluate_offline(str(store), request))
            output["storePath"] = str(store)
        else:
            seed = seed_store(store)
            output = {
                "mode": "offline-adk",
                "storePath": str(store),
                "seed": seed,
                "runs": [
                    _evaluate_subprocess(store, "switch", "--poe-ports-min", "8"),
                    _evaluate_subprocess(store, "switch", "--poe-ports-min", "12"),
                    _evaluate_subprocess(store, "camera", "--quantity", "4"),
                    _evaluate_subprocess(store, "camera", "--quantity", "2"),
                    _evaluate_subprocess(store, "ups"),
                ],
            }
    except subprocess.CalledProcessError as error:
        parser.exit(2, f"error: evaluación secundaria falló: {error.stderr.strip()}\n")
    except (OSError, ValueError, RelateError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
