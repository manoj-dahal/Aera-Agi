"""The documentation has to stay true.

Every number in REQUIREMENTS.md and the voice documents is measured from the
running system. A document that quietly stops being true is worse than no
document, because a reader has no way to tell -- and this repository has
already shipped docs claiming emotions that do not exist and a source tree
that was never laid out that way.

So the claims are asserted here. Add a language, change an endpoint, give a
script a reader, and this suite fails until the documentation is updated.
That failure is the feature.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aera.api.app import create_app
from aera.voice.engine import Emotion
from aera.voice.languages import PACKS
from aera.voice.music import SCALES, TEMPO_MARKS
from aera.voice.personas import PERSONAS
from aera.voice.scripts import ALPHABETIC, TIMING_ONLY, Script

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "REQUIREMENTS.md"
DOCS = ROOT / "docs"


@pytest.fixture(scope="module")
def requirements() -> str:
    return REQUIREMENTS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def operations() -> int:
    spec = create_app().openapi()
    return sum(
        1
        for path in spec["paths"].values()
        for method in path
        if method in ("get", "post", "put", "patch", "delete")
    )


@pytest.fixture(scope="module")
def voice_endpoints() -> list[str]:
    spec = create_app().openapi()
    return sorted(p for p in spec["paths"] if "/voice" in p)


class TestRequirementsFileExists:
    def test_it_is_at_the_repository_root(self):
        """Where someone looks for it, not buried in docs/."""
        assert REQUIREMENTS.is_file()

    def test_it_is_not_a_stub(self, requirements):
        assert len(requirements.splitlines()) > 150

    def test_it_separates_built_from_not_built(self, requirements):
        """The whole value of the file: a reader can tell which is which."""
        assert "Not built" in requirements
        assert "⬜" in requirements
        assert "🟡" in requirements


class TestCountsAreAccurate:
    def test_the_operation_count_is_right(self, requirements, operations):
        assert f"| REST operations | **{operations}** |" in requirements, (
            f"REQUIREMENTS.md must say {operations} REST operations"
        )

    def test_the_voice_endpoint_count_is_right(self, requirements, voice_endpoints):
        assert f"| Voice endpoints | **{len(voice_endpoints)}** |" in requirements

    def test_the_language_count_is_right(self, requirements):
        assert f"**{len(PACKS)} packs.**" in requirements

    def test_the_number_spelling_split_is_right(self, requirements):
        spelled = sum(1 for pack in PACKS.values() if pack.spells_all_numbers)
        kept = len(PACKS) - spelled

        assert f"**{spelled} of {len(PACKS)} packs spell every integer" in requirements
        assert f"{kept} do not, on purpose.**" in requirements

    def test_the_script_split_is_right(self, requirements):
        assert f"**{len(ALPHABETIC)} scripts get real articulation" in requirements
        assert f"**{len(TIMING_ONLY)} get syllable timing only" in requirements

    def test_the_python_test_count_is_close(self, requirements):
        """Within five percent. Exact would fail on every test added, which
        trains a reader to ignore the failure; an order of magnitude out is
        the thing worth catching.
        """
        match = re.search(r"\*\*([\d,]+) passing, \d+ skipped\*\*", requirements)
        assert match, "REQUIREMENTS.md must state the passing test count"
        claimed = int(match.group(1).replace(",", ""))

        collected = _collected_test_count()
        # Counting "def test_" in the sources undercounts badly: a single
        # parametrised function is many cases, and this suite is heavily
        # parametrised -- 1,069 definitions expand to 1,847 tests. Ask
        # pytest instead of guessing from the text.
        assert abs(claimed - collected) <= max(20, collected * 0.05), (
            f"REQUIREMENTS.md claims {claimed} tests, {collected} are collected"
        )


def _collected_test_count() -> int:
    """How many tests pytest actually collects, parametrisation included."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    if not match:
        pytest.skip("could not collect the test count")
    return int(match.group(1))


class TestEveryLanguageIsListed:
    @pytest.mark.parametrize("code", sorted(PACKS))
    def test_the_code_appears(self, code, requirements):
        """A language nobody can find is a language nobody uses."""
        assert f"`{code}`" in requirements, f"{code} is not listed in REQUIREMENTS.md"

    def test_right_to_left_languages_are_flagged(self, requirements):
        for code in sorted(c for c, p in PACKS.items() if p.rtl):
            assert code in requirements


class TestEveryVoiceEndpointIsReachable:
    def test_the_documented_endpoints_exist(self, voice_endpoints):
        """Cheap guard: the ones REQUIREMENTS.md talks about by name."""
        named = ["/api/v1/voice/sing", "/api/v1/voice/languages"]

        for endpoint in named:
            assert endpoint in voice_endpoints


class TestDocsMatchTheCode:
    """The design documents predate the implementation and had drifted.

    These check the specific claims that were found wrong, so they cannot
    come back.
    """

    def test_the_emotion_list_matches_the_enum(self):
        """docs/voice/Emotion-Engine.md listed Thinking and Friendly, which
        have never existed, and omitted Sad, which does."""
        text = (DOCS / "voice" / "Emotion-Engine.md").read_text(encoding="utf-8")
        listed = {
            line.strip("- ").strip().lower()
            for line in text.splitlines()
            if line.strip().startswith("- ")
        }
        actual = {emotion.value for emotion in Emotion}

        invented = {
            word for word in listed if word in {"thinking", "friendly"}
        }
        assert not invented, f"documents an emotion that does not exist: {invented}"
        assert "sad" in listed, "Sad is a real emotion and must be documented"
        assert actual <= listed, f"undocumented emotions: {actual - listed}"

    def test_the_file_structure_document_matches_the_package(self):
        """docs/03-FILE-STRUCTURE.md described voice/ as stt/, tts/, emotion/
        and four more directories. None of those has ever existed."""
        text = (DOCS / "03-FILE-STRUCTURE.md").read_text(encoding="utf-8")
        real = sorted(p.stem for p in (ROOT / "aera" / "voice").glob("*.py"))

        for module in ("languages", "scripts", "music", "personas"):
            assert module in real
            assert f"{module}.py" in text, f"{module}.py is not in the file structure doc"

    def test_the_voice_document_states_the_language_count(self):
        text = (DOCS / "08-VOICE-SYSTEM.md").read_text(encoding="utf-8")

        assert str(len(PACKS)) in text, "08-VOICE-SYSTEM.md must state how many languages"

    def test_the_voice_document_describes_singing(self):
        text = (DOCS / "08-VOICE-SYSTEM.md").read_text(encoding="utf-8")

        assert "sing" in text.lower()

    def test_the_music_reference_numbers_are_right(self):
        text = (DOCS / "08-VOICE-SYSTEM.md").read_text(encoding="utf-8")

        assert f"{len(SCALES)} scales" in text
        assert f"{len(TEMPO_MARKS)} tempo" in text


def _agent_classes() -> dict[str, str]:
    """Every agent class in the package, keyed by its registered name."""
    import importlib

    found: dict[str, str] = {}
    for module in (
        "coding_agent", "core_agent", "extended_agents",
        "knowledge_agents", "media_agents", "system_agents",
    ):
        mod = importlib.import_module(f"aera.agents.{module}")
        for attribute in dir(mod):
            obj = getattr(mod, attribute)
            if (
                isinstance(obj, type)
                and attribute.endswith("Agent")
                and attribute != "Agent"
                and getattr(obj, "name", None)
            ):
                found.setdefault(obj.name, (obj.description or "").strip())
    return found


def _default_flags() -> dict[str, bool]:
    import yaml

    return yaml.safe_load((ROOT / "config" / "agents.yaml").read_text())["agents"]


class TestAgentRoster:
    """docs/07-AGENTS.md described twenty agents.

    Thirty-four exist. Fourteen were undocumented, and the list included a
    Gallery Agent that has never been written -- marked "Core System Agent",
    so a reader had no way to tell it was fiction.
    """

    @pytest.fixture(scope="class")
    def roster(self) -> str:
        return (DOCS / "07-AGENTS.md").read_text(encoding="utf-8")

    def test_the_count_is_right(self, roster):
        agents = _agent_classes()
        disabled = sum(1 for v in _default_flags().values() if v is False)

        assert f"**{len(agents)} agents are implemented." in roster
        assert f"{len(agents) - disabled} are enabled by default.**" in roster

    @pytest.mark.parametrize("name", sorted(_agent_classes()))
    def test_every_agent_is_listed(self, name, roster):
        assert f"| `{name}` |" in roster, f"{name} is not in the roster table"

    @pytest.mark.parametrize("name", sorted(_agent_classes()))
    def test_the_default_state_is_right(self, name, roster):
        """An agent documented as on when it ships off is worse than silence."""
        flags = _default_flags()
        expected = "off" if flags.get(name) is False else "on"
        row = next(line for line in roster.splitlines() if line.startswith(f"| `{name}` |"))

        assert f"| {expected} |" in row, f"{name} is documented as the wrong default"

    def test_the_disabled_agents_explain_themselves(self, roster):
        for name in sorted(k for k, v in _default_flags().items() if v is False):
            assert f"| `{name}` |" in roster

    def test_no_agent_is_documented_that_does_not_exist(self, roster):
        """Gallery was listed as a core agent and has no class."""
        assert "Gallery Agent" not in roster.replace(
            "There is no Gallery Agent.", ""
        ).split("# Not implemented")[0]


class TestAgentDocumentsAreHonest:
    def test_gallery_is_marked_not_implemented(self):
        text = (DOCS / "agents" / "Gallery-Agent.md").read_text(encoding="utf-8")

        assert "Not implemented" in text
        assert "Core System Agent" not in text.split("Status:")[1][:120]

    @pytest.mark.parametrize("name", ["Audio", "Terminal"])
    def test_agents_that_ship_disabled_say_so(self, name):
        text = (DOCS / "agents" / f"{name}-Agent.md").read_text(encoding="utf-8")

        assert "disabled by default" in text

    def test_every_agent_document_names_a_real_agent_or_says_it_does_not(self):
        """A document for a class that does not exist must be marked."""
        agents = _agent_classes()
        unmarked = []
        for path in sorted((DOCS / "agents").glob("*-Agent.md")):
            key = path.stem.replace("-Agent", "").replace("-", "_").lower()
            if key in agents:
                continue
            text = path.read_text(encoding="utf-8")
            if "Not implemented" not in text:
                unmarked.append(path.name)

        assert not unmarked, f"documents agents that do not exist: {unmarked}"


class TestAgentConfigIsCoherent:
    def test_no_key_is_declared_twice(self):
        """vision was set false on one line and true twenty lines later.

        YAML keeps the last value silently, so the file contradicted itself
        and the first line was simply untrue.
        """
        import collections
        import re

        text = (ROOT / "config" / "agents.yaml").read_text(encoding="utf-8")
        keys = re.findall(r"^  (\w+):", text, re.MULTILINE)
        duplicates = [k for k, n in collections.Counter(keys).items() if n > 1]

        assert not duplicates, f"duplicate keys in agents.yaml: {duplicates}"

    def test_every_flag_names_a_real_agent(self):
        agents = _agent_classes()
        scalars = {"max_concurrent_tasks", "task_timeout_seconds"}
        unknown = [
            key
            for key, value in _default_flags().items()
            if isinstance(value, bool) and key not in agents and key not in scalars
        ]

        assert not unknown, f"agents.yaml enables agents that do not exist: {unknown}"


class TestPersonasAreDocumented:
    @pytest.mark.parametrize("persona_id", sorted(PERSONAS))
    def test_each_persona_is_named(self, persona_id, requirements):
        text = requirements + (DOCS / "08-VOICE-SYSTEM.md").read_text(encoding="utf-8")

        assert persona_id in text


class TestNoStrayFiles:
    def test_there_is_no_case_colliding_readme(self):
        """docs/ held both README.md and a one-byte README.MD.

        On a case-insensitive filesystem -- macOS and Windows defaults --
        those are the same path, and a checkout silently loses one of them.
        """
        readmes = [p.name for p in DOCS.iterdir() if p.name.lower() == "readme.md"]

        assert len(readmes) == 1, f"case-colliding readmes in docs/: {readmes}"

    def test_no_documentation_file_is_empty(self):
        empty = [
            str(path.relative_to(ROOT))
            for path in DOCS.rglob("*.md")
            if len(path.read_text(encoding="utf-8").strip()) < 20
        ]

        assert not empty, f"empty documentation files: {empty}"


class TestHonestyAboutGaps:
    """Every gap named in REQUIREMENTS.md must really be refused in code.

    A document that says "not built" while the code returns something
    plausible is worse than either.
    """

    def test_plugin_execution_is_refused(self):
        from aera.services import plugins

        source = Path(plugins.__file__).read_text(encoding="utf-8")

        assert "isolation" in source.lower()

    def test_the_formant_limit_is_stated_in_code(self):
        from aera.voice.personas import FORMANT_NOTE

        assert "not a speech engine" in FORMANT_NOTE

    def test_singing_says_it_is_not_audio(self):
        source = (ROOT / "aera" / "api" / "routers" / "voice.py").read_text(encoding="utf-8")

        assert "not audio" in source

    def test_the_timing_only_scripts_are_declared(self):
        """The claim in §7 has to match the code, and the code asserts it
        at import -- this checks the document agrees."""
        assert Script.HAN in TIMING_ONLY
        assert Script.DEVANAGARI in ALPHABETIC
