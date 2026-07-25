"""AERA command-line interface.

    aera serve            start the API + dashboard
    aera chat "..."       one-shot chat from the terminal
    aera repl             interactive session
    aera status           system snapshot
    aera memory ...       inspect / search the memory graph
    aera agents           list agents and capabilities
    aera index PATH       index a project folder
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from . import __version__
from .core.config import load_config
from .core.errors import AeraError
from .core.kernel import Kernel
from .core.logging import setup_logging


def _print(data: Any, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data if isinstance(data, str) else json.dumps(data, indent=2, default=str))


async def _with_kernel(args) -> Kernel:
    config = load_config(args.config)
    if args.quiet:
        config.logging.level = "WARNING"
    kernel = Kernel(config)
    await kernel.start()
    return kernel


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_serve(args) -> int:
    import uvicorn

    from .api.app import create_app

    config = load_config(args.config)
    host = args.host or config.api.host
    port = args.port or config.api.port

    setup_logging(config.logging.level, json_format=config.logging.json_format)
    print(f"\n  ◈ AERA v{__version__}")
    print(f"    dashboard  http://{'localhost' if host == '0.0.0.0' else host}:{port}/")
    print(f"    api docs   http://{'localhost' if host == '0.0.0.0' else host}:{port}/docs")
    print(f"    websocket  ws://{'localhost' if host == '0.0.0.0' else host}:{port}/ws\n")

    uvicorn.run(
        create_app(config),
        host=host,
        port=port,
        log_config=None,
        access_log=False,
        reload=False,
    )
    return 0


async def cmd_chat(args) -> int:
    kernel = await _with_kernel(args)
    try:
        result = await kernel.chat(args.message, conversation_id="cli", agent=args.agent)
        if args.json:
            _print(result.to_public(), as_json=True)
        else:
            print(f"\n[{result.agent}] {result.output}\n")
        return 0 if result.success else 1
    finally:
        await kernel.stop()


async def cmd_repl(args) -> int:
    kernel = await _with_kernel(args)
    print(f"\n  ◈ AERA v{__version__} — interactive. Type /exit to quit, /status for info.\n")
    try:
        while True:
            try:
                line = input("you › ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line in ("/exit", "/quit", "/q"):
                break
            if line == "/status":
                _print(kernel.status(), as_json=True)
                continue
            if line == "/agents":
                for agent in kernel.registry.status():
                    print(f"  {agent['name']:<14} {agent['status']:<9} {agent['tasks_completed']} tasks")
                continue
            result = await kernel.chat(line, conversation_id="repl")
            print(f"\naera ({result.agent}) › {result.output}\n")
        return 0
    finally:
        await kernel.stop()


async def cmd_status(args) -> int:
    kernel = await _with_kernel(args)
    try:
        _print(kernel.status(), as_json=True)
        return 0
    finally:
        await kernel.stop()


async def cmd_agents(args) -> int:
    kernel = await _with_kernel(args)
    try:
        if args.json:
            _print(kernel.registry.status(), as_json=True)
        else:
            print(f"\n{len(kernel.registry)} agents\n")
            for agent in kernel.registry.status():
                caps = ", ".join(agent["capabilities"][:4])
                print(f"  {agent['name']:<14} {agent['status']:<9} {caps}")
            print()
        return 0
    finally:
        await kernel.stop()


async def cmd_memory(args) -> int:
    kernel = await _with_kernel(args)
    try:
        if args.action == "stats":
            _print(kernel.memory.stats(), as_json=True)
        elif args.action == "search":
            results = await kernel.memory.recall(args.query or "", limit=args.limit)
            if args.json:
                _print([r.to_public() for r in results], as_json=True)
            else:
                for i, r in enumerate(results, 1):
                    print(f"  {i}. [{r.score:.2f}] {r.node.title}\n     {r.node.summary(110)}")
        elif args.action == "store":
            node = await kernel.memory.store(
                title=args.query or "note", content=args.query or "", creator="cli"
            )
            print(f"stored {node.id}")
        return 0
    finally:
        await kernel.stop()


async def cmd_index(args) -> int:
    kernel = await _with_kernel(args)
    try:
        project = kernel.workspace.open(args.path, index=True)
        stored = await kernel.workspace.sync_to_memory()
        summary = kernel.workspace.summary()
        print(f"\nindexed {project.name}")
        print(f"  root      {summary['root']}")
        print(f"  files     {summary['files']}  (skipped {summary['skipped']})")
        print(f"  lines     {summary['total_lines']}")
        print(f"  symbols   {summary['symbols']}")
        print(f"  languages {', '.join(list(summary['languages'])[:8])}")
        print(f"  memory    {stored} nodes\n")
        return 0
    finally:
        await kernel.stop()


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aera", description="AERA AI Operating System")
    parser.add_argument("--version", action="version", version=f"AERA {__version__}")
    parser.add_argument("--config", default=None, help="configuration directory (default: ./config)")
    parser.add_argument("--quiet", "-q", action="store_true", help="reduce log output")
    parser.add_argument("--json", action="store_true", help="machine-readable output")

    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="start the API server and dashboard")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)
    serve.set_defaults(func=cmd_serve, is_async=False)

    chat = sub.add_parser("chat", help="send a single message")
    chat.add_argument("message")
    chat.add_argument("--agent", default=None, help="force a specific agent")
    chat.set_defaults(func=cmd_chat, is_async=True)

    repl = sub.add_parser("repl", help="interactive session")
    repl.set_defaults(func=cmd_repl, is_async=True)

    status = sub.add_parser("status", help="system status")
    status.set_defaults(func=cmd_status, is_async=True)

    agents = sub.add_parser("agents", help="list agents")
    agents.set_defaults(func=cmd_agents, is_async=True)

    memory = sub.add_parser("memory", help="inspect the memory graph")
    memory.add_argument("action", choices=["stats", "search", "store"], default="stats", nargs="?")
    memory.add_argument("query", nargs="?", default="")
    memory.add_argument("--limit", type=int, default=10)
    memory.set_defaults(func=cmd_memory, is_async=True)

    index = sub.add_parser("index", help="index a project folder")
    index.add_argument("path")
    index.set_defaults(func=cmd_index, is_async=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if getattr(args, "is_async", False):
            return asyncio.run(args.func(args))
        return args.func(args)
    except AeraError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
