"""Workspace, automation, voice and hologram tests."""

from __future__ import annotations

import pytest

from aera.automation import (
    Action,
    ActionType,
    AutomationEngine,
    RunStatus,
    Trigger,
    TriggerType,
)
from aera.core.errors import NotFoundError, SandboxViolation, ValidationError, WorkflowError
from aera.hologram import AvatarEmotion, Gesture, HologramController
from aera.voice import Emotion, VoiceEngine, detect_emotion, generate_visemes
from aera.workspace import WorkspaceIndexer


@pytest.fixture
def sample_project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "import os\n\n\nclass Application:\n    def run(self):\n        return 1\n\n\ndef main():\n    Application().run()\n"
    )
    (tmp_path / "src" / "utils.py").write_text("def helper(x):\n    return x * 2\n")
    (tmp_path / "app.js").write_text("export function boot() { return true; }\n")
    (tmp_path / "README.md").write_text("# Sample project\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("// ignored\n")
    return tmp_path


class TestWorkspaceIndexer:
    def test_open_and_detect_kind(self, sample_project):
        indexer = WorkspaceIndexer()
        project = indexer.open(sample_project)
        assert "python" in project.kinds

    def test_missing_path(self):
        with pytest.raises(NotFoundError):
            WorkspaceIndexer().open("/definitely/not/here")

    def test_file_not_directory(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        with pytest.raises(ValidationError):
            WorkspaceIndexer().open(f)

    def test_ignores_configured_dirs(self, sample_project):
        indexer = WorkspaceIndexer()
        project = indexer.open(sample_project)
        assert not any("node_modules" in p for p in project.files)

    def test_indexes_expected_files(self, sample_project):
        project = WorkspaceIndexer().open(sample_project)
        assert project.files  # main.py, utils.py, app.js, README.md, pyproject.toml
        assert "src/main.py" in project.files

    def test_extracts_symbols(self, sample_project):
        indexer = WorkspaceIndexer()
        indexer.open(sample_project)
        names = {s["name"] for s in indexer.active_project.files["src/main.py"].symbols}
        assert {"Application", "run", "main"} <= names

    def test_language_counts(self, sample_project):
        project = WorkspaceIndexer().open(sample_project)
        assert project.languages.get("python") == 2

    def test_search_ranks_by_name(self, sample_project):
        indexer = WorkspaceIndexer()
        indexer.open(sample_project)
        results = indexer.search("utils helper")
        assert results and results[0]["path"] == "src/utils.py"

    def test_search_finds_symbols(self, sample_project):
        indexer = WorkspaceIndexer()
        indexer.open(sample_project)
        assert any(r["path"] == "src/main.py" for r in indexer.search("application"))

    def test_search_without_project(self):
        assert WorkspaceIndexer().search("anything") == []

    def test_read_file(self, sample_project):
        indexer = WorkspaceIndexer()
        indexer.open(sample_project)
        assert "class Application" in indexer.read_file("src/main.py")["content"]

    def test_read_file_traversal_blocked(self, sample_project):
        indexer = WorkspaceIndexer()
        indexer.open(sample_project)
        with pytest.raises(SandboxViolation):
            indexer.read_file("../../../etc/passwd")

    def test_read_missing_file(self, sample_project):
        indexer = WorkspaceIndexer()
        indexer.open(sample_project)
        with pytest.raises(NotFoundError):
            indexer.read_file("nope.py")

    def test_skips_oversized_files(self, sample_project):
        # comfortably above the 2 MB max_file_size_bytes default
        (sample_project / "huge.py").write_text("x = 1\n" * 500_000)
        indexer = WorkspaceIndexer()
        project = indexer.open(sample_project)
        assert "huge.py" not in project.files and project.skipped >= 1

    def test_reindex_is_idempotent(self, sample_project):
        indexer = WorkspaceIndexer()
        project = indexer.open(sample_project)
        before = len(project.files)
        indexer.index()
        assert len(indexer.active_project.files) == before

    async def test_sync_to_memory(self, sample_project, memory):
        indexer = WorkspaceIndexer(memory=memory)
        indexer.open(sample_project)
        stored = await indexer.sync_to_memory()
        assert stored >= 1
        assert (await memory.recall("sample project"))


class TestAutomationEngine:
    @pytest.fixture
    def engine(self, router, memory, registry, bus):
        return AutomationEngine(router=router, memory=memory, registry=registry, bus=bus)

    async def test_sequential_actions(self, engine):
        wf = engine.create(
            name="seq",
            actions=[
                Action(type=ActionType.SET_VARIABLE, params={"a": 1}),
                Action(type=ActionType.LOG, params={"message": "value {{ a }}"}, store_as="out"),
            ],
        )
        run = await engine.run(wf.id)
        assert run.status == RunStatus.SUCCESS
        assert run.variables["out"] == "value 1"

    async def test_variable_interpolation_nested(self, engine):
        wf = engine.create(
            name="nested",
            variables={"user": {"name": "Ada"}},
            actions=[Action(type=ActionType.LOG, params={"message": "hi {{ user.name }}"}, store_as="m")],
        )
        run = await engine.run(wf.id)
        assert run.variables["m"] == "hi Ada"

    async def test_unresolved_variable_left_alone(self, engine):
        wf = engine.create(
            name="unresolved",
            actions=[Action(type=ActionType.LOG, params={"message": "{{ missing }}"}, store_as="m")],
        )
        run = await engine.run(wf.id)
        assert run.variables["m"] == "{{ missing }}"

    async def test_condition_then_branch(self, engine):
        wf = engine.create(
            name="cond",
            actions=[
                Action(
                    type=ActionType.CONDITION,
                    params={"left": 5, "operator": "greater_than", "right": 3},
                    then=[Action(type=ActionType.SET_VARIABLE, params={"branch": "then"})],
                    otherwise=[Action(type=ActionType.SET_VARIABLE, params={"branch": "else"})],
                )
            ],
        )
        run = await engine.run(wf.id)
        assert run.variables["branch"] == "then"

    async def test_condition_else_branch(self, engine):
        wf = engine.create(
            name="cond2",
            actions=[
                Action(
                    type=ActionType.CONDITION,
                    params={"left": "a", "operator": "equals", "right": "b"},
                    then=[Action(type=ActionType.SET_VARIABLE, params={"branch": "then"})],
                    otherwise=[Action(type=ActionType.SET_VARIABLE, params={"branch": "else"})],
                )
            ],
        )
        run = await engine.run(wf.id)
        assert run.variables["branch"] == "else"

    async def test_loop_for_each(self, engine):
        wf = engine.create(
            name="loop",
            actions=[
                Action(
                    type=ActionType.LOOP,
                    params={"for_each": ["x", "y", "z"]},
                    body=[Action(type=ActionType.LOG, params={"message": "{{ item }}"})],
                )
            ],
        )
        run = await engine.run(wf.id)
        assert run.status == RunStatus.SUCCESS
        # nested body steps are recorded as they run, so the LOOP step lands last
        assert run.steps[-1].output["iterations"] == 3
        assert len(run.steps) == 4  # 3 body executions + the loop itself

    async def test_loop_bounded_by_max_iterations(self, engine):
        wf = engine.create(
            name="bounded",
            max_iterations=5,
            actions=[
                Action(type=ActionType.LOOP, params={"times": 1000},
                       body=[Action(type=ActionType.LOG, params={"message": "x"})])
            ],
        )
        run = await engine.run(wf.id)
        assert run.steps[-1].output["iterations"] == 5

    async def test_failure_stops_run(self, engine):
        wf = engine.create(
            name="fail",
            actions=[
                Action(type=ActionType.PUBLISH_EVENT, params={}),  # missing topic
                Action(type=ActionType.SET_VARIABLE, params={"never": True}),
            ],
        )
        run = await engine.run(wf.id)
        assert run.status == RunStatus.FAILED
        assert "never" not in run.variables

    async def test_continue_on_error(self, engine):
        wf = engine.create(
            name="tolerant",
            actions=[
                Action(type=ActionType.PUBLISH_EVENT, params={}, continue_on_error=True),
                Action(type=ActionType.SET_VARIABLE, params={"reached": True}),
            ],
        )
        run = await engine.run(wf.id)
        assert run.status == RunStatus.SUCCESS and run.variables["reached"] is True

    async def test_ai_and_agent_actions(self, engine):
        wf = engine.create(
            name="ai",
            actions=[
                Action(type=ActionType.AI_GENERATE, params={"prompt": "hello"}, store_as="reply"),
                Action(type=ActionType.AGENT_TASK,
                       params={"capability": "planning", "input": "plan it"}, store_as="plan"),
            ],
        )
        run = await engine.run(wf.id)
        assert run.status == RunStatus.SUCCESS
        assert run.variables["reply"] and run.variables["plan"]

    async def test_memory_actions(self, engine, memory):
        wf = engine.create(
            name="mem",
            actions=[
                Action(type=ActionType.MEMORY_STORE,
                       params={"title": "From workflow", "content": "automation wrote this"},
                       store_as="node_id"),
                Action(type=ActionType.MEMORY_SEARCH, params={"query": "automation"}, store_as="hits"),
            ],
        )
        run = await engine.run(wf.id)
        assert run.variables["node_id"] and run.variables["hits"]

    async def test_notify_publishes_event(self, engine, bus):
        seen = []
        await bus.subscribe("notification.created", lambda e: seen.append(e.payload))
        wf = engine.create(
            name="notify",
            actions=[Action(type=ActionType.NOTIFY, params={"title": "T", "message": "M"})],
        )
        await engine.run(wf.id)
        assert seen and seen[0]["message"] == "M"

    async def test_event_trigger(self, engine, bus):
        wf = engine.create(
            name="on-event",
            triggers=[Trigger(type=TriggerType.EVENT, value="custom.fired")],
            actions=[Action(type=ActionType.LOG, params={"message": "triggered"})],
        )
        await engine.install_triggers()
        await bus.publish("custom.fired", {"n": 1})
        assert any(r.workflow_id == wf.id and r.status == RunStatus.SUCCESS for r in engine.runs)
        await engine.shutdown()

    async def test_disabled_workflow_refuses(self, engine):
        wf = engine.create(name="off", enabled=False, actions=[])
        with pytest.raises(WorkflowError):
            await engine.run(wf.id)

    async def test_missing_workflow(self, engine):
        with pytest.raises(ValidationError):
            await engine.run("ghost")

    async def test_lookup_by_name(self, engine):
        engine.create(name="by-name", actions=[])
        assert engine.get("by-name").name == "by-name"

    async def test_history_capped(self, engine):
        wf = engine.create(name="many", actions=[])
        engine._max_runs = 5
        for _ in range(8):
            await engine.run(wf.id)
        assert len(engine.runs) == 5

    def test_condition_operators(self, engine):
        ev = engine._evaluate
        assert ev({"left": 1, "operator": "equals", "right": 1}, {})
        assert ev({"left": "abc", "operator": "contains", "right": "b"}, {})
        assert ev({"left": "", "operator": "empty"}, {})
        assert ev({"left": "x", "operator": "exists"}, {})
        assert not ev({"left": 1, "operator": "less_than", "right": 0}, {})
        with pytest.raises(WorkflowError):
            ev({"left": 1, "operator": "wat", "right": 1}, {})


class TestVoice:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("This is absolutely amazing!!", Emotion.EXCITED),
            ("Warning: this is risky", Emotion.CONCERNED),
            ("Sorry, that failed", Emotion.SAD),
            ("critical security vulnerability", Emotion.SERIOUS),
            ("The build is done, great work", Emotion.HAPPY),
        ],
    )
    def test_emotion_detection(self, text, expected):
        assert detect_emotion(text)[0] == expected

    def test_neutral_default(self):
        assert detect_emotion("the file is at /tmp/x")[0] == Emotion.NEUTRAL

    def test_empty_text(self):
        emotion, confidence = detect_emotion("")
        assert emotion == Emotion.NEUTRAL and confidence == 0.0

    def test_visemes_generated(self):
        frames = generate_visemes("hello world", 1000)
        assert frames and all("t" in f and "shape" in f for f in frames)

    def test_visemes_empty_input(self):
        assert generate_visemes("", 1000) == []

    async def test_speak_produces_timing(self, config, bus):
        engine = VoiceEngine(config.voice, bus=bus)
        result = await engine.speak("Hello there, this is a test of the voice system")
        assert result.duration_ms > 0 and result.visemes

    async def test_speak_empty_raises(self, config):
        with pytest.raises(ValueError):
            await VoiceEngine(config.voice).speak("   ")

    async def test_speak_publishes_avatar_sync(self, config, bus):
        engine = VoiceEngine(config.voice, bus=bus)
        seen = []
        await bus.subscribe("avatar.emotion", lambda e: seen.append(e.payload))
        await engine.speak("Fantastic, everything works!")
        assert seen and "emotion" in seen[0]

    async def test_listen_and_wake_word(self, config):
        engine = VoiceEngine(config.voice)
        await engine.start_listening()
        transcript = await engine.listen(b"AERA what is the status")
        assert transcript.text.startswith("AERA")
        assert engine.detect_wake_word(transcript.text)

    async def test_status(self, config):
        assert VoiceEngine(config.voice).status()["enabled"] is True


class TestHologram:
    async def test_show_hide(self, bus):
        h = HologramController(bus=bus)
        assert (await h.show()).visible is True
        assert (await h.hide()).visible is False

    async def test_emotion_sets_blendshapes(self, bus):
        h = HologramController(bus=bus)
        state = await h.set_emotion(AvatarEmotion.HAPPY, intensity=1.0)
        assert state.emotion == AvatarEmotion.HAPPY and state.blendshapes["smile"] > 0

    async def test_intensity_scales_expression(self, bus):
        h = HologramController(bus=bus)
        strong = (await h.set_emotion("happy", intensity=1.0)).blendshapes["smile"]
        weak = (await h.set_emotion("happy", intensity=0.2)).blendshapes["smile"]
        assert strong > weak

    async def test_invalid_emotion(self, bus):
        with pytest.raises(ValueError):
            await HologramController(bus=bus).set_emotion("banana")

    async def test_gesture(self, bus):
        assert (await HologramController(bus=bus).play_gesture(Gesture.WAVE)).gesture == Gesture.WAVE

    async def test_gaze_clamped(self, bus):
        state = await HologramController(bus=bus).look_at(5.0, -9.0)
        assert state.gaze == (1.0, -1.0)

    async def test_lipsync_lookup(self, bus):
        h = HologramController(bus=bus)
        await h.start_speaking([{"t": 0, "shape": "open"}, {"t": 500, "shape": "closed"}])
        assert h.lipsync_at(0) == "open"
        assert h.lipsync_at(600) == "closed"
        await h.stop_speaking()
        assert h.state.speaking is False

    async def test_publishes_events(self, bus):
        seen = []
        await bus.subscribe("avatar.*", lambda e: seen.append(e.topic))
        await HologramController(bus=bus).set_emotion("calm")
        assert "avatar.emotion" in seen

    async def test_sync_with_voice(self, bus):
        h = HologramController(bus=bus)
        await h.sync_with_voice({"emotion": "excited", "intensity": 0.9, "visemes": [{"t": 0, "shape": "open"}]})
        assert h.state.emotion == AvatarEmotion.EXCITED and h.state.speaking is True

    def test_idle_frame(self, bus):
        frame = HologramController(bus=bus).idle_frame()
        assert {"breath", "blink", "sway"} <= set(frame)


class TestKernel:
    async def test_starts_and_reports(self, kernel):
        status = kernel.status()
        assert status["ready"] is True and status["agents"]["total"] > 0

    async def test_chat_end_to_end(self, kernel):
        result = await kernel.chat("write a python function", conversation_id="k1")
        assert result.success and result.output

    async def test_memory_persists_across_turns(self, kernel):
        await kernel.chat("my favourite database is postgres", conversation_id="k2")
        assert len(kernel.memory.conversation_history("k2")) == 2

    async def test_subsystems_present(self, kernel):
        for attr in ("memory", "router", "registry", "workspace", "automation", "voice", "hologram", "vault"):
            assert getattr(kernel, attr) is not None

    async def test_agents_reach_workspace(self, kernel):
        assert kernel.registry.ctx.workspace is kernel.workspace
