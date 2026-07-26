# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""System-facing agents: memory, workspace, git, terminal, security,
performance and notifications."""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import time
from pathlib import Path
from typing import Any

from ..core.errors import PermissionDeniedError, SandboxViolation
from .base import Agent, Capability, Task, TaskResult


class MemoryAgent(Agent):
    """Stores, recalls and maintains the shared Memory Graph."""

    name = "memory"
    description = "Manages memory storage, recall, consolidation and graph maintenance."
    capabilities = (Capability.MEMORY,)
    priority = 9

    async def handle(self, task: Task) -> TaskResult:
        action = str(task.context.get("action", "recall")).lower()
        memory = self.ctx.memory

        if action == "store":
            node = await memory.store(
                title=task.context.get("title") or task.input[:70],
                content=task.input,
                tags=task.context.get("tags", []),
                importance=float(task.context.get("importance", 0.6)),
                creator=task.requester,
                project_id=task.project_id,
                conversation_id=task.conversation_id,
            )
            return TaskResult(
                task_id=task.id, agent=self.name,
                output=f"Stored memory '{node.title}'.",
                data={"node": node.to_public()}, memory_ids=[node.id],
            )

        if action == "consolidate":
            stats = await memory.consolidate()
            return TaskResult(
                task_id=task.id, agent=self.name,
                output=f"Consolidated memory: promoted {stats['promoted']}, pruned {stats['pruned']}.",
                data=stats,
            )

        if action == "stats":
            stats = memory.stats()
            return TaskResult(
                task_id=task.id, agent=self.name,
                output=f"Memory graph holds {stats['nodes']} nodes and {stats['edges']} edges.",
                data=stats,
            )

        # default: recall
        results = await memory.recall(
            task.input, limit=int(task.context.get("limit", 8)), project_id=task.project_id
        )
        if not results:
            return TaskResult(
                task_id=task.id, agent=self.name,
                output="I have no memories matching that yet.",
                data={"results": []},
            )
        lines = [
            f"{i}. {r.node.title} — {r.node.summary(140)} (score {r.score:.2f})"
            for i, r in enumerate(results, 1)
        ]
        return TaskResult(
            task_id=task.id, agent=self.name,
            output="Here is what I remember:\n" + "\n".join(lines),
            data={"results": [r.to_public() for r in results]},
            memory_ids=[r.node.id for r in results],
        )


class WorkspaceAgent(Agent):
    """Understands projects: structure, languages, dependencies."""

    name = "workspace"
    description = "Analyses project structure, indexes files and answers questions about them."
    capabilities = (Capability.WORKSPACE, Capability.FILE_ANALYSIS)
    priority = 8

    async def handle(self, task: Task) -> TaskResult:
        indexer = task.context.get("indexer") or getattr(self.ctx, "workspace", None)
        if indexer is None:
            return await self._llm_answer(task, "")

        project = indexer.active_project
        if project is None:
            return TaskResult(
                task_id=task.id, agent=self.name,
                output="No workspace is open. Open a project folder first.",
                data={"project": None},
            )

        summary = indexer.summary()
        matches = indexer.search(task.input, limit=8) if task.input.strip() else []
        detail = "\n".join(f"- {m['path']} ({m['language']}, {m['lines']} lines)" for m in matches)
        context = (
            f"Project: {summary.get('name')} at {summary.get('root')}\n"
            f"Files indexed: {summary.get('files')} | Languages: "
            f"{', '.join(summary.get('languages', {}))}\n"
        )
        if detail:
            context += f"Relevant files:\n{detail}"

        result = await self._llm_answer(task, context)
        result.data.update({"project": summary, "matches": matches})
        return result

    async def _llm_answer(self, task: Task, context: str) -> TaskResult:
        system = (
            "You are AERA's Workspace Agent. Answer questions about the user's project "
            "using the indexed facts below. Never invent files or paths that are not listed."
        )
        if context:
            system += f"\n\n{context}"
        response = await self.ctx.router.complete(
            task.input or "Summarise this project.",
            task="default", system=system, temperature=0.3,
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider, data={},
        )


class GitAgent(Agent):
    """Repository analysis and Git assistance."""

    name = "git"
    description = "Analyses repositories, drafts commit messages and explains Git workflows."
    capabilities = (Capability.GIT,)
    priority = 8

    _SAFE = {"status", "log", "diff", "branch", "remote", "show", "rev-parse"}

    async def handle(self, task: Task) -> TaskResult:
        repo = task.context.get("repo_path") or task.context.get("project_root")
        info: dict[str, Any] = {}

        if repo and shutil.which("git"):
            info = await self._inspect(Path(repo))

        context = ""
        if info.get("is_repo"):
            context = (
                f"Repository: {info.get('root')}\n"
                f"Branch: {info.get('branch')}\n"
                f"Changed files: {info.get('changed_files')}\n"
                f"Recent commits:\n{info.get('recent_log', '')}"
            )

        system = (
            "You are AERA's Git Agent. Give exact, copy-pasteable git commands. "
            "Warn before anything destructive (reset --hard, push --force, clean -fd)."
        )
        if context:
            system += f"\n\nCurrent repository state:\n{context}"

        response = await self.ctx.router.complete(
            task.input, task="default", system=system, temperature=0.3
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider, data={"repo": info},
        )

    async def _inspect(self, root: Path) -> dict[str, Any]:
        """Read-only repository probe using safe git subcommands."""
        async def run(*args: str) -> str:
            if args[0] not in self._SAFE:
                raise PermissionDeniedError(f"git {args[0]} is not permitted here")
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", str(root), *args,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await proc.communicate()
            return out.decode("utf-8", "replace").strip()

        try:
            top = await run("rev-parse", "--show-toplevel")
            if not top:
                return {"is_repo": False}
            status = await run("status", "--porcelain")
            return {
                "is_repo": True,
                "root": top,
                "branch": await run("rev-parse", "--abbrev-ref", "HEAD"),
                "changed_files": len([ln for ln in status.splitlines() if ln.strip()]),
                "recent_log": await run("log", "--oneline", "-5"),
            }
        except (OSError, PermissionDeniedError):
            return {"is_repo": False}


class TerminalAgent(Agent):
    """Executes shell commands under a strict allowlist."""

    name = "terminal"
    description = "Runs allowlisted shell commands and explains their output."
    capabilities = (Capability.TERMINAL,)
    priority = 6

    async def handle(self, task: Task) -> TaskResult:
        security = getattr(self.ctx.config, "security", None)
        allowed = set(getattr(security, "terminal_allowlist", []) or [])
        enabled = bool(getattr(security, "allow_terminal", False))
        command = task.context.get("command") or task.input

        if not enabled:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error="Terminal execution is disabled. Set security.allow_terminal=true to enable it.",
                output="Terminal execution is disabled by policy.",
            )

        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return TaskResult(task_id=task.id, agent=self.name, success=False,
                              error=f"could not parse command: {exc}")
        if not parts:
            return TaskResult(task_id=task.id, agent=self.name, success=False,
                              error="empty command")
        if parts[0] not in allowed:
            raise SandboxViolation(
                f"command '{parts[0]}' is not in the terminal allowlist",
                details={"allowlist": sorted(allowed)},
            )

        cwd = task.context.get("cwd") or os.getcwd()
        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *parts, cwd=cwd,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            return TaskResult(task_id=task.id, agent=self.name, success=False,
                              error="command timed out after 30s")
        except OSError as exc:
            return TaskResult(task_id=task.id, agent=self.name, success=False, error=str(exc))

        out = stdout.decode("utf-8", "replace")
        err = stderr.decode("utf-8", "replace")
        return TaskResult(
            task_id=task.id, agent=self.name,
            success=proc.returncode == 0,
            output=out or err,
            error=err if proc.returncode != 0 else None,
            data={
                "command": command,
                "exit_code": proc.returncode,
                "stdout": out[:8000],
                "stderr": err[:4000],
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )


class SecurityAgent(Agent):
    """Security review and policy guidance."""

    name = "security"
    description = "Reviews security posture, permissions and vulnerabilities."
    capabilities = (Capability.SECURITY,)
    priority = 8
    model_task = "reasoning"

    async def handle(self, task: Task) -> TaskResult:
        system = (
            "You are AERA's Security Agent operating under a zero-trust policy. "
            "Assess risk honestly, rank findings by severity (critical/high/medium/low), "
            "and give a concrete remediation for each. You assist with defensive security, "
            "hardening and authorised auditing only - never with attacking systems the user "
            "does not own or is not explicitly authorised to test."
        )
        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.3
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
        )


class PerformanceAgent(Agent):
    """Reports runtime metrics and advises on optimisation."""

    name = "performance"
    description = "Monitors system performance and suggests optimisations."
    capabilities = (Capability.PERFORMANCE,)
    priority = 6

    async def handle(self, task: Task) -> TaskResult:
        metrics = self._snapshot()
        system = (
            "You are AERA's Performance Agent. Use the live metrics below to give "
            "specific, measurable optimisation advice. Do not invent numbers.\n\n"
            f"Metrics: {metrics}"
        )
        response = await self.ctx.router.complete(
            task.input or "How is the system performing?",
            task="default", system=system, temperature=0.3,
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider, data={"metrics": metrics},
        )

    def _snapshot(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "memory_graph": self.ctx.memory.stats(),
            "providers": self.ctx.router.stats(),
        }
        if self.ctx.registry is not None:
            data["agents"] = self.ctx.registry.summary()
        # Real host readings rather than a rough estimate.
        from ..services.telemetry import get_telemetry

        data["host"] = get_telemetry().snapshot()
        return data


class NotificationAgent(Agent):
    """Creates and broadcasts user-facing notifications."""

    name = "notification"
    description = "Formats and dispatches notifications to the dashboard."
    capabilities = (Capability.NOTIFICATION,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        level = str(task.context.get("level", "info")).lower()
        title = task.context.get("title") or "AERA"
        payload = {
            "title": title,
            "message": task.input,
            "level": level,
            "timestamp": time.time(),
        }
        await self.ctx.bus.publish("notification.created", payload, source=self.name)
        return TaskResult(
            task_id=task.id, agent=self.name,
            output=f"Notification sent: {title}", data=payload,
        )
