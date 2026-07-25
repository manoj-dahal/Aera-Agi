"""AERA AGI — command-line entry point.

Usage:
    python -m src.main            # start the server
    python -m src.main serve      # start the server
    python -m src.main info       # show system information
"""

from __future__ import annotations

import argparse
import sys

from src import __version__


def cmd_serve() -> None:
    from src.server import run

    run()


def cmd_info() -> None:
    from src.bootstrap import boot

    system = boot()
    print(f"AERA AGI v{__version__}")
    print(f"  agents : {', '.join(system.agents.agents)}")
    stats = system.memory.stats()
    print(f"  memory : {stats.nodes} nodes, {stats.edges} edges")
    system.shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aera", description="AERA AI Operating System")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve", "info"])
    parser.add_argument("--version", action="version", version=f"AERA {__version__}")
    args = parser.parse_args(argv)

    if args.command == "serve":
        cmd_serve()
    elif args.command == "info":
        cmd_info()
    return 0


if __name__ == "__main__":
    sys.exit(main())
