# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Additional agents from the requirements roster.

Only agents whose work the current stack can genuinely perform are implemented
here. Capabilities that need a model or subsystem AERA does not yet have
(vision, OCR, audio transcription, live web access) are deliberately absent
rather than stubbed into something that fabricates output.
"""

from __future__ import annotations

import platform
import shutil
import time
from pathlib import Path
from typing import Any

from .base import Agent, Capability, Task, TaskResult


class EthicalHackingAgent(Agent):
    """Authorised, defensive security assessment.

    Scoped tightly on purpose: this agent reasons about hardening and reviews
    systems the user controls. It does not perform live scanning, exploitation,
    or any action against a remote host.
    """

    name = "ethical_hacking"
    description = (
        "Assists with authorised defensive security work: vulnerability review, "
        "hardening guidance and threat modelling."
    )
    capabilities = (Capability.SECURITY,)
    priority = 7
    model_task = "reasoning"

    #: Refusal triggers - requests aimed at systems the user does not own.
    _UNAUTHORISED = (
        "without permission", "without authorization", "without authorisation",
        "someone else's", "not my ", "target company", "break into",
        "steal", "exfiltrate", "ransomware", "botnet", "ddos",
    )

    async def handle(self, task: Task) -> TaskResult:
        lowered = task.input.lower()
        if any(marker in lowered for marker in self._UNAUTHORISED):
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                success=False,
                output=(
                    "I only assist with security work on systems you own or are "
                    "explicitly authorised to test. Tell me which system you are "
                    "responsible for and I will help you harden or assess it."
                ),
                error="request appears to target an unauthorised system",
            )

        system = (
            "You are AERA's Ethical Hacking Agent, operating strictly in a defensive, "
            "authorised capacity. You help the user secure systems they own: threat "
            "modelling, vulnerability review, configuration hardening, dependency "
            "auditing and detection guidance.\n\n"
            "Structure findings as: Scope and assumptions, Findings ranked by severity "
            "(critical/high/medium/low), Remediation for each, and Verification steps. "
            "Never provide working exploit code, credential-harvesting techniques, or "
            "instructions aimed at systems the user does not control. If a request "
            "crosses that line, say so plainly and offer the defensive equivalent."
        )
        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.25
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={"scope": "defensive", "authorised_only": True},
        )


class AutomationAgent(Agent):
    """Designs and triggers workflows."""

    name = "automation"
    description = "Designs automation workflows and runs them through the engine."
    capabilities = (Capability.AUTOMATION,)
    priority = 7

    async def handle(self, task: Task) -> TaskResult:
        engine = getattr(self.ctx, "automation", None)
        existing = engine.list() if engine is not None else []

        system = (
            "You are AERA's Automation Agent. Express the user's request as a concrete "
            "workflow: an ordered list of actions drawn from ai_generate, agent_task, "
            "memory_store, memory_search, notify, publish_event, set_variable, wait, "
            "condition and loop. State the trigger, the actions in order, and what "
            "success looks like."
        )
        if existing:
            names = ", ".join(w["name"] for w in existing[:8])
            system += f"\n\nWorkflows already registered: {names}"

        response = await self.ctx.router.complete(
            task.input, task="reasoning", system=system, temperature=0.3
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={"registered_workflows": len(existing)},
        )


class SchedulerAgent(Agent):
    """Reports and reasons about scheduled work."""

    name = "scheduler"
    description = "Manages scheduled jobs and reports on upcoming automation."
    capabilities = (Capability.AUTOMATION,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        engine = getattr(self.ctx, "automation", None)
        scheduled: list[dict[str, Any]] = []
        if engine is not None:
            scheduled = [
                w for w in engine.list() if "schedule" in w.get("triggers", [])
            ]
        runs = engine.history(10) if engine is not None else []

        lines = [f"{len(scheduled)} scheduled workflow(s)."]
        for workflow in scheduled:
            lines.append(f"- {workflow['name']} ({workflow['actions']} actions)")
        if runs:
            lines.append(f"\nLast {len(runs)} run(s):")
            for run in runs[-5:]:
                lines.append(f"- {run['workflow_name']}: {run['status']}")

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output="\n".join(lines),
            data={"scheduled": len(scheduled), "recent_runs": len(runs)},
        )


class DeviceAgent(Agent):
    """Reports on the host machine and any connected devices."""

    name = "device"
    description = "Reports host machine details and manages connected devices."
    capabilities = (Capability.DEVICE,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        info: dict[str, Any] = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "python": platform.python_version(),
            "paired_devices": 0,
        }
        try:
            usage = shutil.disk_usage(Path.home())
            info["disk_free_gb"] = round(usage.free / 1e9, 1)
            info["disk_total_gb"] = round(usage.total / 1e9, 1)
        except OSError:
            pass

        summary = (
            f"Host: {info['system']} {info['release']} on {info['machine']}. "
            f"No mobile devices are paired - the companion app and pairing "
            f"transport are not part of this build."
        )
        return TaskResult(task_id=task.id, agent=self.name, output=summary, data=info)


class UpdateAgent(Agent):
    """Reports component versions and update status."""

    name = "update"
    description = "Tracks component versions and reports available updates."
    capabilities = (Capability.PERFORMANCE,)
    priority = 4

    async def handle(self, task: Task) -> TaskResult:
        from .. import __version__

        components = {
            "aera": __version__,
            "python": platform.python_version(),
            "auto_update": getattr(self.ctx.config, "system", None)
            and self.ctx.config.system.auto_update,
        }
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=(
                f"AERA {__version__} on Python {platform.python_version()}. "
                "No update channel is configured, so no remote version check was made."
            ),
            data=components,
        )


class BackupAgent(Agent):
    """Persists and reports on memory-graph snapshots."""

    name = "backup"
    description = "Creates and reports on memory graph backups."
    capabilities = (Capability.MEMORY,)
    priority = 4

    async def handle(self, task: Task) -> TaskResult:
        action = str(task.context.get("action", "status")).lower()

        if action == "backup":
            path = self.ctx.memory.save()
            if path is None:
                return TaskResult(
                    task_id=task.id, agent=self.name, success=False,
                    error="no storage path is configured for the memory graph",
                )
            size = path.stat().st_size if path.exists() else 0
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                output=f"Memory graph saved to {path} ({size} bytes).",
                data={"path": str(path), "bytes": size, "at": time.time()},
            )

        stats = self.ctx.memory.stats()
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=(
                f"{stats['nodes']} nodes and {stats['edges']} edges are eligible for "
                "backup. Snapshots are written on shutdown and every maintenance cycle."
            ),
            data=stats,
        )


class LearningAgent(Agent):
    """Surfaces patterns in stored memory."""

    name = "learning"
    description = "Detects patterns and preferences across the memory graph."
    capabilities = (Capability.LEARNING,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        graph = self.ctx.memory.graph
        nodes = graph.find(limit=300)

        tag_counts: dict[str, int] = {}
        creator_counts: dict[str, int] = {}
        for node in nodes:
            for tag in node.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            creator_counts[node.creator] = creator_counts.get(node.creator, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda kv: -kv[1])[:8]
        top_creators = sorted(creator_counts.items(), key=lambda kv: -kv[1])[:5]
        frequent = sorted(nodes, key=lambda n: -n.access_count)[:5]

        lines = [f"Analysed {len(nodes)} memories."]
        if top_tags:
            lines.append("Recurring themes: " + ", ".join(f"{t} ({c})" for t, c in top_tags))
        if top_creators:
            lines.append("Most active sources: " + ", ".join(f"{c} ({n})" for c, n in top_creators))
        if frequent and frequent[0].access_count > 0:
            lines.append(
                "Most recalled: "
                + ", ".join(f"{n.title} (x{n.access_count})" for n in frequent if n.access_count)
            )

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output="\n".join(lines),
            data={
                "analysed": len(nodes),
                "top_tags": dict(top_tags),
                "top_creators": dict(top_creators),
            },
        )


class MonitoringAgent(Agent):
    """Watches subsystem health."""

    name = "monitoring"
    description = "Monitors subsystem health and reports anomalies."
    capabilities = (Capability.PERFORMANCE,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        registry = self.ctx.registry
        provider_stats = self.ctx.router.stats()

        failing = [
            name for name, stats in provider_stats.items()
            if stats["requests"] > 0 and stats["failures"] / stats["requests"] > 0.5
        ]
        agent_errors = []
        if registry is not None:
            agent_errors = [
                a["name"] for a in registry.status() if a["status"] == "error" or a["last_error"]
            ]

        healthy = not failing and not agent_errors
        lines = ["All monitored subsystems are healthy."] if healthy else []
        if failing:
            lines.append("Providers failing more than half their requests: " + ", ".join(failing))
        if agent_errors:
            lines.append("Agents reporting errors: " + ", ".join(agent_errors))

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output="\n".join(lines),
            data={
                "healthy": healthy,
                "failing_providers": failing,
                "agents_with_errors": agent_errors,
            },
        )
