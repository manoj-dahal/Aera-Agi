# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Tests for the skill catalogue, manager and background engines.

The contract under test is self-knowledge: AERA must report what it cannot do
rather than routing work to a skill whose backend is missing.
"""

from __future__ import annotations

import pytest

from aera.skills import (
    SKILLS,
    SKILLS_BY_ID,
    Availability,
    Backend,
    ContextEngine,
    LearningEngine,
    PlanningEngine,
    ReasoningEngine,
    SkillCategory,
    SkillManager,
    category_counts,
    skills_in,
)


@pytest.fixture
async def manager(registry, router, config):
    m = SkillManager(registry=registry, router=router, config=config)
    await m.resolve()
    return m


class TestCatalogue:
    def test_every_category_is_populated(self):
        for category in SkillCategory:
            assert skills_in(category), f"no skills in {category.value}"

    def test_all_seventeen_categories(self):
        assert len(category_counts()) == 17

    def test_ids_are_unique(self):
        ids = [s.id for s in SKILLS]
        assert len(ids) == len(set(ids))

    def test_lookup_index_is_complete(self):
        assert len(SKILLS_BY_ID) == len(SKILLS)

    def test_every_skill_names_an_agent_and_backend(self):
        for skill in SKILLS:
            assert skill.agent, f"{skill.id} has no agent"
            assert isinstance(skill.backend, Backend)
            assert skill.description.strip()

    def test_skills_reference_real_agents(self, registry, config):
        """A skill must point at an agent that can exist."""
        from aera.agents import AGENT_CLASSES

        known = {
            cls.name
            for classes in AGENT_CLASSES.values()
            for cls in classes
        }
        unknown = {s.agent for s in SKILLS} - known
        assert not unknown, f"skills reference unknown agents: {unknown}"

    def test_background_skills_are_marked(self):
        background = [s for s in SKILLS if s.background]
        assert len(background) >= 15
        # Memory recall and indexing must run without being asked.
        assert SKILLS_BY_ID["memory_recall"].background
        assert SKILLS_BY_ID["automatic_indexing"].background


class TestAvailability:
    async def test_resolves_every_skill(self, manager):
        assert len(manager.all()) == len(SKILLS)
        assert all(s.availability is not None for s in manager.all())

    async def test_most_skills_are_available_offline(self, manager):
        """The built-in reasoner should unlock the bulk of the catalogue."""
        assert len(manager.available()) > len(SKILLS) * 0.6

    async def test_missing_backends_are_reported_not_hidden(self, manager):
        ocr = manager.get("ocr")
        assert ocr is not None
        # No Tesseract in CI: it must be listed but flagged.
        assert ocr.availability is Availability.NEEDS_BACKEND
        assert ocr.reason

    async def test_unavailable_skills_always_explain_why(self, manager):
        for state in manager.unavailable():
            assert state.reason, f"{state.skill.id} is unavailable with no reason"

    async def test_policy_gated_skills_are_disabled(self, manager, config):
        """Terminal is off by default; its skills must say so."""
        terminal = manager.get("terminal_automation")
        assert terminal is not None
        assert terminal.availability is not Availability.AVAILABLE

    async def test_backend_probe_covers_every_backend(self, manager):
        backends = await manager.probe_backends()
        for backend in Backend:
            assert backend in backends, f"backend not probed: {backend.value}"


class TestMatching:
    @pytest.mark.parametrize(
        "query,expected",
        [
            ("generate unit tests", "unit_test_generation"),
            ("translate this to japanese", "translation"),
            ("extract text from a scan", "ocr"),
            ("what is my cpu usage", "pc_monitoring"),
            ("brainstorm some ideas", "brainstorming"),
            ("refactor this class", "refactoring"),
            ("backup my memory", "backup_restore"),
        ],
    )
    async def test_matches_the_right_skill(self, manager, query, expected):
        matches = manager.match(query, limit=3)
        assert matches, f"no match for {query!r}"
        assert expected in [m.skill.id for m in matches]

    async def test_empty_query_matches_nothing(self, manager):
        assert manager.match("") == []
        assert manager.match("   ") == []

    async def test_available_only_filters_gated_skills(self, manager):
        every = manager.match("extract text from a scanned page", limit=10)
        usable = manager.match("extract text from a scanned page", limit=10, available_only=True)
        assert len(usable) <= len(every)
        assert all(m.availability is Availability.AVAILABLE for m in usable)

    async def test_match_carries_the_unavailability_reason(self, manager):
        matches = manager.match("run ocr on this image", limit=5)
        ocr = next((m for m in matches if m.skill.id == "ocr"), None)
        assert ocr is not None and ocr.reason

    async def test_best_agent_skips_unavailable_skills(self, manager):
        result = manager.best_agent_for("write a python function")
        assert result is not None
        agent, match = result
        assert match.availability is Availability.AVAILABLE
        assert agent == match.skill.agent


class TestReasoningEngine:
    @pytest.mark.parametrize(
        "text,complexity",
        [
            ("hi", "trivial"),
            ("write a python function to sort a list", "simple"),
            ("migrate the db and then update the api and then deploy it", "complex"),
        ],
    )
    async def test_grades_complexity(self, manager, text, complexity):
        assert ReasoningEngine(skills=manager).assess(text).complexity == complexity

    async def test_flags_planning_for_complex_work(self, manager):
        engine = ReasoningEngine(skills=manager)
        assert engine.assess("first do this and then that and then the other").needs_planning
        assert not engine.assess("hello").needs_planning

    async def test_detects_memory_dependent_requests(self, manager):
        engine = ReasoningEngine(skills=manager)
        assert engine.assess("what did i say last time about the schema").needs_memory

    async def test_reports_a_capability_gap(self, manager):
        """When the best match cannot run, say so explicitly."""
        result = ReasoningEngine(skills=manager).assess("run ocr on this scanned invoice")
        assert result.unavailable_reason is not None
        assert "unavailable" in result.unavailable_reason

    async def test_suggests_an_available_agent(self, manager):
        result = ReasoningEngine(skills=manager).assess("refactor this python module")
        assert result.suggested_agent == "coding"
        assert result.suggested_skill

    async def test_rationale_is_always_present(self, manager):
        assert ReasoningEngine(skills=manager).assess("anything at all").rationale


class TestPlanningEngine:
    async def test_splits_a_multi_step_goal(self, manager):
        steps = PlanningEngine(skills=manager).decompose(
            "index the project and then generate docs and then commit"
        )
        assert len(steps) == 3
        assert [s.index for s in steps] == [1, 2, 3]

    async def test_maps_steps_to_skills(self, manager):
        steps = PlanningEngine(skills=manager).decompose("write tests and then commit")
        assert any(s.skill for s in steps)

    async def test_single_goal_yields_one_step(self, manager):
        assert len(PlanningEngine(skills=manager).decompose("write a function")) == 1

    async def test_respects_the_step_cap(self, manager):
        goal = " and then ".join(f"task {i}" for i in range(20))
        assert len(PlanningEngine(skills=manager).decompose(goal, max_steps=4)) == 4


class TestContextEngine:
    async def test_tracks_the_active_project(self, memory, bus):
        engine = ContextEngine(memory=memory, bus=bus)
        await engine.update(project_id="p1", project_name="demo")
        assert engine.context.project_name == "demo"

    async def test_publishes_on_a_project_switch(self, memory, bus):
        engine = ContextEngine(memory=memory, bus=bus)
        seen: list[str] = []
        await bus.subscribe("context.switched", lambda e: seen.append(e.topic))
        await engine.update(project_id="p1")
        await engine.update(project_id="p2")
        assert seen == ["context.switched"]

    async def test_no_switch_event_on_first_project(self, memory, bus):
        engine = ContextEngine(memory=memory, bus=bus)
        seen: list[str] = []
        await bus.subscribe("context.switched", lambda e: seen.append(e.topic))
        await engine.update(project_id="p1")
        assert seen == []

    async def test_writes_into_working_memory(self, memory, bus):
        engine = ContextEngine(memory=memory, bus=bus)
        await engine.update(conversation_id="c1")
        assert memory.get_working("active_context")

    async def test_ignores_unknown_fields(self, memory, bus):
        engine = ContextEngine(memory=memory, bus=bus)
        await engine.update(not_a_field="x")  # must not raise
        assert engine.snapshot()["conversation_id"] is None


class TestLearningEngine:
    async def test_records_outcomes(self, manager, memory):
        engine = LearningEngine(skills=manager, memory=memory)
        await engine.observe(agent="coding", skill_id="code_generation", success=True)
        await engine.observe(agent="coding", skill_id="code_generation", success=False)
        state = manager.get("code_generation")
        assert state.invocations == 2 and state.failures == 1
        assert state.success_rate == 0.5

    async def test_surfaces_struggling_skills(self, manager, memory):
        engine = LearningEngine(skills=manager, memory=memory)
        for _ in range(4):
            await engine.observe(agent="coding", skill_id="debugging", success=False)
        struggling = engine.insights()["struggling"]
        assert any(s["skill"] == "debugging" for s in struggling)

    async def test_reports_capability_gaps(self, manager, memory):
        gaps = LearningEngine(skills=manager, memory=memory).insights()["capability_gaps"]
        assert gaps and all("reason" in g for g in gaps)

    async def test_consolidates_into_memory(self, manager, memory):
        engine = LearningEngine(skills=manager, memory=memory)
        await engine.observe(agent="coding", skill_id="code_generation", success=True)
        await engine.consolidate()
        assert await memory.recall("usage pattern")


class TestKernelIntegration:
    async def test_engines_are_wired(self, kernel):
        for attr in ("skills", "context_engine", "reasoning_engine",
                     "planning_engine", "learning_engine"):
            assert getattr(kernel, attr) is not None, f"{attr} not wired"

    async def test_status_includes_skills(self, kernel):
        status = kernel.status()
        assert status["skills"]["total"] == len(SKILLS)
        assert status["skills"]["available"] > 0

    async def test_learning_engine_observes_dispatched_tasks(self, kernel):
        await kernel.chat("write a python function", conversation_id="s1")
        assert kernel.learning_engine.insights()["observations"] > 0

    async def test_agents_can_reach_the_skill_manager(self, kernel):
        assert kernel.registry.ctx.skills is kernel.skills


class TestSkillsApi:
    def test_endpoints(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as client:
            catalogue = client.get("/api/v1/skills").json()["data"]
            assert catalogue["count"] == len(SKILLS)

            assert client.get("/api/v1/skills/summary").json()["data"]["total"] == len(SKILLS)
            assert client.get("/api/v1/skills/backends").json()["success"] is True

            gaps = client.get("/api/v1/skills/gaps").json()["data"]["gaps"]
            assert all(g["reason"] for g in gaps)

            matches = client.post("/api/v1/skills/match?q=write+unit+tests").json()["data"]
            assert matches["count"] > 0

            one = client.get("/api/v1/skills/code_generation").json()["data"]
            assert one["id"] == "code_generation"

            assert client.get("/api/v1/skills/nope").status_code == 404

    def test_filters(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as client:
            coding = client.get("/api/v1/skills?category=coding").json()["data"]
            assert coding["count"] == len(skills_in(SkillCategory.CODING))

            usable = client.get("/api/v1/skills?available_only=true").json()["data"]
            assert all(s["availability"] == "available" for s in usable["skills"])
