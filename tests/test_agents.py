"""Agent framework, routing and specialist agent tests."""

from __future__ import annotations

import pytest

from aera.agents import Capability, CoreAgent, Task
from aera.agents.base import Agent, AgentStatus, TaskResult
from aera.agents.coding_agent import detect_language, extract_code_blocks
from aera.core.errors import AgentNotFoundError


class TestIntentDetection:
    @pytest.fixture
    def core(self, agent_context):
        return CoreAgent(agent_context)

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("write a python function to parse json", Capability.CODING),
            ("refactor this class for readability", Capability.CODING),
            ("debug this traceback please", Capability.DEBUGGING),
            ("review my code for security issues", Capability.CODE_REVIEW),
            ("git commit and push my branch", Capability.GIT),
            ("plan the steps to migrate the database", Capability.PLANNING),
            ("translate this into Spanish", Capability.TRANSLATION),
            ("research the best vector databases", Capability.RESEARCH),
            ("remember that I prefer dark mode", Capability.MEMORY),
            ("check for vulnerabilities in the auth flow", Capability.SECURITY),
            ("the app is slow, optimize it", Capability.PERFORMANCE),
            ("automate this workflow every day", Capability.AUTOMATION),
            ("what files are in the project", Capability.WORKSPACE),
        ],
    )
    def test_routes_correctly(self, core, text, expected):
        capability, confidence = core.detect_intent(text)
        assert capability == expected
        assert confidence > 0.5

    def test_empty_input(self, core):
        capability, confidence = core.detect_intent("")
        assert capability == Capability.CONVERSATION
        assert confidence == 0.0

    def test_smalltalk_stays_conversational(self, core):
        assert core.detect_intent("hello there")[0] == Capability.CONVERSATION


class TestLanguageDetection:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("write a python decorator", "python"),
            ("build a flutter widget in dart", "dart"),
            ("create a react component in typescript", "typescript"),
            ("write a rust struct with cargo", "rust"),
            ("golang http handler", "go"),
        ],
    )
    def test_detects(self, text, expected):
        assert detect_language(text) == expected

    def test_fence_wins(self):
        assert detect_language("here:\n```go\nfunc main(){}\n```") == "go"

    def test_default(self):
        assert detect_language("do something vague") == "python"

    def test_extract_code_blocks(self):
        blocks = extract_code_blocks("text\n```python\nx = 1\n```\nmore\n```js\ny=2\n```")
        assert blocks == [("python", "x = 1"), ("js", "y=2")]

    def test_extract_none(self):
        assert extract_code_blocks("no code at all") == []


class TestRegistry:
    def test_builds_all_agents(self, registry):
        names = registry.names()
        for expected in ("core", "coding", "memory", "planning", "research", "security"):
            assert expected in names

    def test_capability_lookup(self, registry):
        assert registry.best_for(Capability.CODING).name == "coding"
        assert registry.best_for(Capability.PLANNING).name == "planning"

    def test_unknown_capability(self, registry):
        assert registry.find_by_capability("not_a_capability") == []

    def test_get_missing_raises(self, registry):
        with pytest.raises(AgentNotFoundError):
            registry.get("ghost")

    def test_capability_map(self, registry):
        cmap = registry.capability_map()
        assert "coding" in cmap and "coding" in cmap["coding"]

    async def test_lifecycle(self, registry):
        await registry.start_all()
        assert all(a.status == AgentStatus.RUNNING for a in registry.agents.values())
        await registry.stop("coding")
        assert registry.get("coding").status == AgentStatus.STOPPED
        await registry.restart("coding")
        assert registry.get("coding").status == AgentStatus.RUNNING
        await registry.stop_all()

    async def test_dispatch_routes_by_capability(self, registry):
        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.CODING, input="write a sort function")
        )
        assert result.success and result.agent == "coding"

    async def test_dispatch_to_named_agent(self, registry):
        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.CONVERSATION, input="hi"), agent_name="reasoning"
        )
        assert result.agent == "reasoning"

    async def test_dispatch_many(self, registry):
        await registry.start_all()
        results = await registry.dispatch_many(
            [
                Task(capability=Capability.CODING, input="a"),
                Task(capability=Capability.PLANNING, input="b"),
            ]
        )
        assert len(results) == 2 and all(r.success for r in results)

    async def test_history_recorded(self, registry):
        await registry.start_all()
        await registry.dispatch(Task(capability=Capability.CODING, input="x"))
        assert len(registry.history()) >= 1

    async def test_summary(self, registry):
        await registry.start_all()
        summary = registry.summary()
        assert summary["total"] == len(registry) and summary["running"] > 0


class TestAgentExecution:
    async def test_failure_is_captured_not_raised(self, agent_context):
        class Exploding(Agent):
            name = "exploding"
            capabilities = (Capability.CONVERSATION,)

            async def handle(self, task):
                raise RuntimeError("intentional failure")

        agent = Exploding(agent_context)
        await agent.start()
        result = await agent.execute(Task(input="x"))
        assert result.success is False
        assert "intentional failure" in result.error
        assert agent.tasks_failed == 1
        # the agent stays usable afterwards
        assert agent.status == AgentStatus.RUNNING

    async def test_metrics_accumulate(self, agent_context):
        class Simple(Agent):
            name = "simple"
            capabilities = (Capability.CONVERSATION,)

            async def handle(self, task):
                return TaskResult(task_id=task.id, agent=self.name, output="ok")

        agent = Simple(agent_context)
        await agent.start()
        for _ in range(3):
            await agent.execute(Task(input="x"))
        assert agent.tasks_completed == 3
        assert agent.describe()["tasks_completed"] == 3

    async def test_can_handle(self, registry):
        assert registry.get("coding").can_handle(Capability.CODING)
        assert not registry.get("coding").can_handle(Capability.GIT)


class TestCoreAgentPipeline:
    async def test_delegates_to_specialist(self, registry):
        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.CONVERSATION, input="write a python function to sort"),
            agent_name="core",
        )
        assert result.data.get("routed_to") == "coding"

    async def test_forced_agent_wins(self, registry):
        await registry.start_all()
        task = Task(capability=Capability.CONVERSATION, input="write python code")
        task.context["force_agent"] = "reasoning"
        result = await registry.dispatch(task, agent_name="core")
        assert result.data.get("routed_to") == "reasoning"

    async def test_persists_conversation(self, registry, memory):
        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.CONVERSATION, input="hello", conversation_id="c9"),
            agent_name="core",
        )
        assert len(result.memory_ids) == 2
        assert len(memory.conversation_history("c9")) == 2

    async def test_recalls_prior_context(self, registry, memory):
        await registry.start_all()
        await memory.store("Deployment", "AERA deploys via docker compose", tags=["ops"])
        result = await registry.dispatch(
            Task(capability=Capability.CONVERSATION, input="how do we deploy?"),
            agent_name="core",
        )
        assert result.success


class TestSpecialistAgents:
    async def test_memory_agent_store_and_recall(self, registry):
        await registry.start_all()
        task = Task(capability=Capability.MEMORY, input="remember this fact")
        task.context["action"] = "store"
        stored = await registry.dispatch(task, agent_name="memory")
        assert stored.success and stored.memory_ids

        recall = Task(capability=Capability.MEMORY, input="remember this fact")
        result = await registry.dispatch(recall, agent_name="memory")
        assert result.success and result.data["results"]

    async def test_memory_agent_stats(self, registry):
        await registry.start_all()
        task = Task(capability=Capability.MEMORY, input="")
        task.context["action"] = "stats"
        result = await registry.dispatch(task, agent_name="memory")
        assert "nodes" in result.data

    async def test_planning_agent_stores_plan(self, registry, memory):
        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.PLANNING, input="plan a database migration")
        )
        assert result.success and result.memory_ids

    async def test_terminal_agent_blocked_by_default(self, registry):
        await registry.start_all()
        registry.register_class(__import__(
            "aera.agents.system_agents", fromlist=["TerminalAgent"]
        ).TerminalAgent)
        task = Task(capability=Capability.TERMINAL, input="ls")
        result = await registry.dispatch(task, agent_name="terminal")
        assert result.success is False
        assert "disabled" in (result.error or "").lower()

    async def test_terminal_agent_rejects_non_allowlisted(self, registry, config):
        from aera.agents.system_agents import TerminalAgent
        from aera.core.errors import SandboxViolation

        config.security.allow_terminal = True
        agent = registry.register_class(TerminalAgent)
        await agent.start()
        task = Task(capability=Capability.TERMINAL, input="rm -rf /")
        with pytest.raises(SandboxViolation):
            await agent.handle(task)

    async def test_terminal_agent_runs_allowlisted(self, registry, config):
        from aera.agents.system_agents import TerminalAgent

        config.security.allow_terminal = True
        agent = registry.register_class(TerminalAgent)
        await agent.start()
        task = Task(capability=Capability.TERMINAL, input="echo hello")
        result = await agent.handle(task)
        assert result.success and "hello" in result.output

    async def test_notification_agent_publishes(self, registry, bus):
        await registry.start_all()
        seen = []
        await bus.subscribe("notification.created", lambda e: seen.append(e.payload))
        await registry.dispatch(
            Task(capability=Capability.NOTIFICATION, input="build finished")
        )
        assert seen and seen[0]["message"] == "build finished"

    async def test_performance_agent_reports_metrics(self, registry):
        await registry.start_all()
        result = await registry.dispatch(
            Task(capability=Capability.PERFORMANCE, input="how is performance?")
        )
        assert result.success and "memory_graph" in result.data["metrics"]
