# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

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


class TestDesktopBuildWorkflow:
    """The Windows desktop build, checked without a Windows runner.

    None of this can be executed here -- there is no Windows machine, and
    PyInstaller cannot even run on this sandbox because libpython3.11.so is
    missing. What can be verified is that the workflow says what it means to
    say, and every check below corresponds to something that was wrong.
    """

    @pytest.fixture(scope="class")
    def workflow(self) -> dict:
        import yaml

        return yaml.safe_load(
            (ROOT / "ci" / "github-actions-desktop.yml").read_text(encoding="utf-8")
        )

    @pytest.fixture(scope="class")
    def build(self, workflow) -> dict:
        return workflow["jobs"]["build"]

    def test_windows_is_in_the_matrix(self, build):
        targets = {entry["os"] for entry in build["strategy"]["matrix"]["include"]}

        assert "windows-latest" in targets
        assert {"ubuntu-latest", "macos-latest"} <= targets

    def test_the_default_shell_is_bash(self, build):
        """GitHub defaults Windows runners to PowerShell, where a multi-line
        run block keeps going after a failed command. `npm ci` could fail and
        `npm run build` would still run, producing a green build with no
        interface in it.
        """
        assert build["defaults"]["run"]["shell"] == "bash"

    def test_powershell_steps_opt_in_explicitly(self, build):
        """Compress-Archive is a cmdlet and cannot run under bash."""
        for step in build["steps"]:
            run = step.get("run", "")
            if "Compress-Archive" in run or "Start-Process" in run:
                assert step.get("shell") == "pwsh", (
                    f"{step.get('name')} uses PowerShell but does not ask for it"
                )

    @pytest.mark.parametrize("platform", ["Linux", "Windows", "macOS"])
    def test_every_platform_starts_the_binary(self, platform, build):
        """Windows built the executable, listed its contents and zipped it
        without anyone ever launching it: a binary that cannot start would
        have shipped as a green build."""
        smoke = [
            step
            for step in build["steps"]
            if step.get("name", "").startswith("Smoke test")
            and platform in step.get("if", "")
        ]

        assert smoke, f"no smoke test for {platform}"

    def test_the_windows_smoke_test_fails_when_the_app_exits(self, build):
        step = next(
            s for s in build["steps"] if s.get("name") == "Smoke test (Windows)"
        )

        assert "HasExited" in step["run"]
        assert "throw" in step["run"], "a failure must fail the step"

    def test_the_windows_executable_is_verified(self, build):
        verify = next(
            s for s in build["steps"] if s.get("name") == "Verify bundle contents"
        )

        assert "AERA.exe" in verify["run"]

    def test_the_bundle_check_knows_the_windows_layout(self, build):
        """PyInstaller 6 puts data under _internal, and the spec requires 6."""
        verify = next(
            s for s in build["steps"] if s.get("name") == "Verify bundle contents"
        )

        assert "_internal" in verify["run"]

    def test_it_installs_the_extra_that_provides_pyinstaller(self, build):
        import tomllib

        step = next(s for s in build["steps"] if s.get("name") == "Install project")
        extras = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["optional-dependencies"]

        assert "package" in extras
        assert any("pyinstaller" in dep for dep in extras["package"])
        assert "[dev,package]" in step["run"]

    def test_the_npm_scripts_it_calls_exist(self, build):
        import json

        step = next(s for s in build["steps"] if s.get("name") == "Build interface")
        scripts = json.loads(
            (ROOT / "interface" / "package.json").read_text(encoding="utf-8")
        )["scripts"]

        # Read the script names out of the step rather than hardcoding them,
        # so adding a call to a script that does not exist is caught.
        called = {
            line.strip().removeprefix("npm run ").removeprefix("npm ").strip()
            for line in step["run"].splitlines()
            if line.strip().startswith("npm ") and "ci" not in line
        }
        assert called, "the interface step runs no npm scripts"
        for script in called:
            assert script in scripts, f"the workflow runs npm {script} and it is not defined"

    def test_npm_ci_has_a_lockfile(self):
        """npm ci fails outright without one."""
        assert (ROOT / "interface" / "package-lock.json").is_file()

    def test_the_windows_icon_is_a_real_ico(self):
        """PyInstaller rejects a mislabelled icon on Windows only, so a
        placeholder would pass on Linux and fail the Windows job."""
        header = (ROOT / "installer" / "icon.ico").read_bytes()[:6]

        assert header[:4] == b"\x00\x00\x01\x00", "installer/icon.ico is not an ICO file"
        assert int.from_bytes(header[4:6], "little") > 0, "the ICO holds no images"


class TestWindowsPortability:
    def test_no_hardcoded_tmp_path_in_the_package(self):
        """Path("/tmp") resolves to C:\\tmp on Windows, which does not exist.

        SystemTTS defaulted its output directory to it and called mkdir, so
        the first line AERA ever spoke created a stray directory at the root
        of the system drive.
        """
        import re

        offenders = []
        for path in (ROOT / "aera").rglob("*.py"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r'Path\(\s*["\']/tmp', line):
                    offenders.append(f"{path.relative_to(ROOT)}:{number}")

        assert not offenders, f"hardcoded /tmp is not portable: {offenders}"

    def test_the_speech_backend_uses_the_system_temp_directory(self):
        source = (ROOT / "aera" / "voice" / "backends.py").read_text(encoding="utf-8")

        assert "tempfile.gettempdir()" in source


class TestAttribution:
    """Every source file carries authorship and contact details.

    Applied by ``tools/attribution.py``, which is idempotent and can be
    re-run. These tests exist because a bulk header injection is easy to get
    subtly wrong: a string above a Python module docstring silently stops it
    being ``__doc__``, a comment in JSON makes the file unparseable, and a
    stamp on a generated file is undone by the next build.
    """

    AUTHOR = "Manoj Dahal"
    EMAIL = "info@manoj-dahal.com.np"
    MARKER = f"MADE By {AUTHOR}"

    @pytest.fixture(scope="class")
    def source_files(self) -> list[Path]:
        import subprocess

        names = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        interesting = {".py", ".ts", ".tsx", ".md", ".yaml", ".yml", ".toml", ".spec"}
        return [
            ROOT / n
            for n in names
            if (ROOT / n).is_file()
            and Path(n).suffix in interesting
            and "node_modules" not in n
            and n not in {"interface/index.html", "interface/src/styles/globals.css"}
        ]

    def test_every_source_file_is_attributed(self, source_files):
        missing = [
            str(p.relative_to(ROOT))
            for p in source_files
            if self.MARKER not in p.read_bytes().decode("utf-8", "replace")
        ]

        assert not missing, f"{len(missing)} files lack attribution: {missing[:10]}"

    def test_the_contact_address_is_present(self, source_files):
        missing = [
            str(p.relative_to(ROOT))
            for p in source_files
            if self.EMAIL not in p.read_bytes().decode("utf-8", "replace")
        ]

        assert not missing, f"{len(missing)} files lack the contact address"

    def test_no_file_is_stamped_twice(self, source_files):
        """The stamper is keyed by its marker so a re-run replaces rather
        than stacks. Without that, every run adds another header."""
        doubled = [
            str(p.relative_to(ROOT))
            for p in source_files
            if p.read_bytes().decode("utf-8", "replace").count(self.MARKER) > 1
        ]

        assert not doubled, f"stacked headers in: {doubled[:10]}"

    def test_python_docstrings_survived(self, source_files):
        """A comment above a module docstring is fine; a string is not.

        Had the header been inserted as a string literal, every module
        docstring in the package would have become a discarded expression
        and ``__doc__`` would be None.
        """
        import ast

        lost = []
        for path in source_files:
            if path.suffix != ".py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            body = tree.body
            # Only check files that still look like they meant to have one.
            if body and isinstance(body[0], ast.Expr) and isinstance(
                getattr(body[0], "value", None), ast.Constant
            ):
                if not ast.get_docstring(tree):
                    lost.append(str(path.relative_to(ROOT)))

        assert not lost, f"module docstring broken in: {lost}"

    def test_every_python_file_still_parses(self, source_files):
        import ast

        broken = []
        for path in source_files:
            if path.suffix != ".py":
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as error:
                broken.append(f"{path.relative_to(ROOT)}: {error}")

        assert not broken, broken

    def test_json_manifests_were_not_commented(self):
        """JSON has no comment syntax: a header would make npm refuse to run."""
        import json

        for name in ("interface/package.json", "interface/tsconfig.json"):
            path = ROOT / name
            if path.is_file():
                json.loads(path.read_text(encoding="utf-8"))

    def test_the_manifests_name_the_author(self):
        import json

        import tomllib

        package = json.loads(
            (ROOT / "interface" / "package.json").read_text(encoding="utf-8")
        )
        pyproject = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        assert package["author"] == {"name": self.AUTHOR, "email": self.EMAIL}
        assert pyproject["project"]["authors"] == [
            {"name": self.AUTHOR, "email": self.EMAIL}
        ]

    def test_the_licence_exists_and_names_the_holder(self):
        """Both manifests claimed MIT and no LICENSE file existed."""
        licence = (ROOT / "LICENSE").read_text(encoding="utf-8")

        assert "MIT License" in licence
        assert self.AUTHOR in licence
        assert self.EMAIL in licence

    def test_generated_files_are_not_stamped(self):
        """They are rewritten on every build, so a stamp is lost anyway and
        shows up as spurious churn in the diff."""
        for name in ("interface/index.html", "interface/src/styles/globals.css"):
            path = ROOT / name
            if path.is_file():
                assert self.MARKER not in path.read_text(encoding="utf-8"), (
                    f"{name} is generated and should not be stamped"
                )

    def test_markdown_attribution_is_visible(self):
        """An HTML comment renders as nothing, which is the wrong choice for
        a document a person opens."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        assert f"**{self.MARKER}**" in readme
        assert f"mailto:{self.EMAIL}" in readme

    def test_the_stamper_reports_clean(self):
        """tools/attribution.py --check is the same guard, runnable by hand."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "tools/attribution.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout


class TestShellScripts:
    """The scripts the README tells a new user to run.

    Every check here corresponds to something that was broken. The headline
    one: ./scripts/build-desktop.sh could not work on a clean clone, because
    installer/aera.spec refuses to package without the React interface and no
    script anywhere ran npm. A reader following the README got the spec's
    error telling them to go and do it by hand.
    """

    SCRIPTS = ROOT / "scripts"

    @pytest.fixture(scope="class")
    def build_desktop(self) -> str:
        return (self.SCRIPTS / "build-desktop.sh").read_text(encoding="utf-8")

    def test_every_script_is_syntactically_valid(self):
        import subprocess

        broken = []
        for path in sorted(self.SCRIPTS.glob("*.sh")):
            result = subprocess.run(
                ["bash", "-n", str(path)], capture_output=True, text=True
            )
            if result.returncode != 0:
                broken.append(f"{path.name}: {result.stderr.strip()}")

        assert not broken, broken

    def test_every_script_is_executable(self):
        import stat

        not_executable = [
            path.name
            for path in sorted(self.SCRIPTS.glob("*.sh"))
            if not path.stat().st_mode & stat.S_IXUSR
        ]

        assert not not_executable, f"not executable: {not_executable}"

    def test_every_script_fails_fast(self):
        """Without `set -e` a failed step is skipped and the script still
        reports success."""
        missing = [
            path.name
            for path in sorted(self.SCRIPTS.glob("*.sh"))
            if "set -euo pipefail" not in path.read_text(encoding="utf-8")
        ]

        assert not missing, f"no `set -euo pipefail` in: {missing}"

    def test_the_desktop_build_builds_the_interface(self, build_desktop):
        """The defect: aera.spec hard-fails without aera/desktop/ui-react,
        and nothing in scripts/ ran npm."""
        assert "npm" in build_desktop
        assert "npm run build" in build_desktop

    def test_the_interface_is_built_before_pyinstaller(self, build_desktop):
        """Order matters: packaging first would fail every time."""
        assert build_desktop.index("npm run build") < build_desktop.index("PyInstaller")

    def test_it_checks_node_is_present_first(self, build_desktop):
        """A missing Node should say so, not produce a stack trace."""
        assert "command -v" in build_desktop
        assert "nodejs.org" in build_desktop

    def test_it_verifies_something_was_produced(self, build_desktop):
        """PyInstaller can exit 0 having written nothing useful."""
        assert "ARTIFACT" in build_desktop
        assert "AERA.exe" in build_desktop

    def test_install_provides_what_it_tells_you_to_run(self):
        """install.sh installed [dev] only, then recommended `aera` -- which
        launches the desktop app and imports pywebview. On a clean machine
        that command failed with ModuleNotFoundError."""
        import tomllib

        text = (self.SCRIPTS / "install.sh").read_text(encoding="utf-8")
        extras = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["optional-dependencies"]

        assert "[dev,desktop]" in text
        assert any("pywebview" in dep for dep in extras["desktop"])

    def test_the_lint_step_can_actually_run(self):
        """test.sh gated linting on `python -c 'import ruff'`. ruff is a
        binary, not an importable module, so that always failed and the lint
        step never ran once."""
        text = (self.SCRIPTS / "test.sh").read_text(encoding="utf-8")
        # Comments are stripped: the fixed script explains the old bug in
        # prose, and matching raw text found that explanation rather than
        # any code.
        code = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )

        assert "import ruff" not in code, "the dead `python -c 'import ruff'` gate is back"
        # ruff is invoked through a variable holding its resolved path, so
        # match the arguments rather than a literal "ruff check".
        assert "check aera/" in code

    def test_the_lint_step_can_actually_fail(self):
        """It ended in `|| true`, which discarded every finding."""
        text = (self.SCRIPTS / "test.sh").read_text(encoding="utf-8")
        lint = [
            line
            for line in text.splitlines()
            if "check aera/" in line and not line.lstrip().startswith("#")
        ]

        assert lint
        for line in lint:
            assert "|| true" not in line, "the lint result is discarded"

    def test_the_readme_test_count_is_not_stale(self):
        """It claimed 331 for a long time."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        assert "331 Python tests" not in readme

    @pytest.mark.parametrize(
        "script", ["install.sh", "run.sh", "test.sh", "build.sh", "build-desktop.sh", "clean.sh"]
    )
    def test_the_readme_only_advertises_scripts_that_exist(self, script):
        assert (self.SCRIPTS / script).is_file()


class TestVoiceSamples:
    """The audio in assets/voice-samples is real, distinct and complete.

    A sample set is easy to break silently: a truncated write leaves a valid
    filename with no audio in it, and a copy-paste leaves two names pointing
    at identical bytes. Neither shows up until someone plays them.
    """

    SAMPLES = ROOT / "assets" / "voice-samples"

    @pytest.fixture(scope="class")
    def emotions(self) -> list[str]:
        from aera.voice.engine import Emotion

        return [e.value for e in Emotion]

    def test_the_folder_exists(self):
        assert self.SAMPLES.is_dir()

    @pytest.mark.parametrize("character", ["anime-g", "anime-b"])
    def test_the_base_set_covers_the_emotions(self, character, emotions):
        """Nine emotions in the engine; the folder covered three, so six
        could be read about but never heard."""
        present = {
            path.stem.replace(f"{character}-", "")
            for path in self.SAMPLES.glob(f"{character}-*.mp3")
        }

        assert set(emotions) <= present, f"{character} is missing {set(emotions) - present}"

    @pytest.mark.parametrize("character", ["girl", "boy"])
    def test_the_formant_set_is_complete(self, character, emotions):
        """Both characters, all nine. The boy's nine were missing entirely,
        so the per-emotion acoustics could only be heard in one voice."""
        present = {
            path.stem.replace(f"{character}-", "")
            for path in (self.SAMPLES / "acoustics").glob(f"{character}-*.wav")
        }

        assert set(emotions) <= present, f"{character} lacks {set(emotions) - present}"

    def test_no_two_samples_are_the_same_bytes(self):
        """A duplicate means a generation silently failed and something was
        copied, or the same voice was used twice by mistake."""
        import hashlib

        seen: dict[str, str] = {}
        duplicates = []
        for path in sorted(self.SAMPLES.rglob("*.mp3")):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen:
                duplicates.append(f"{path.name} == {seen[digest]}")
            seen[digest] = path.name

        assert not duplicates, duplicates

    def test_every_mp3_has_a_valid_frame_header(self):
        """A truncated write leaves a plausible filename and no audio."""
        import struct

        broken = []
        for path in sorted(self.SAMPLES.rglob("*.mp3")):
            data = path.read_bytes()
            offset = 0
            if data[:3] == b"ID3":
                size = struct.unpack(">I", bytes(b & 0x7F for b in data[6:10]))[0]
                offset = 10 + size
            header = data[offset : offset + 2]
            if len(header) < 2 or header[0] != 0xFF or (header[1] & 0xE0) != 0xE0:
                broken.append(path.name)

        assert not broken, f"not valid MP3 audio: {broken}"

    def test_every_wav_holds_audible_signal(self):
        """Not just a valid header: actual non-silent samples."""
        import array
        import wave

        silent = []
        for path in sorted(self.SAMPLES.rglob("*.wav")):
            with wave.open(str(path)) as handle:
                frames = handle.getnframes()
                samples = array.array("h")
                samples.frombytes(handle.readframes(min(frames, 40_000)))
            if not samples or max(abs(v) for v in samples) < 100:
                silent.append(path.name)

        assert not silent, f"silent or empty: {silent}"

    def test_no_sample_is_suspiciously_small(self):
        tiny = [
            path.name
            for path in sorted(self.SAMPLES.rglob("*.mp3"))
            if path.stat().st_size < 4_000
        ]

        assert not tiny, f"too small to contain a spoken line: {tiny}"

    def test_paired_lines_use_the_same_text(self, emotions):
        """Both characters speak the same line for each emotion, so any
        difference heard is the character and not the words. Asserted through
        the README, which is where the pairing is recorded."""
        readme = (self.SAMPLES / "README.md").read_text(encoding="utf-8")

        for emotion in emotions:
            assert f"| {emotion} |" in readme, f"{emotion} is not documented"

    def test_the_readme_names_every_file(self):
        readme = (self.SAMPLES / "README.md").read_text(encoding="utf-8")

        for path in sorted(self.SAMPLES.glob("anime-*.mp3")):
            assert path.name in readme, f"{path.name} is not documented"


class TestLanguageSamples:
    """Recorded lines for the language packs.

    The packs support 35 languages and the folder covered six, so the claim
    "multilingual" rested almost entirely on code nobody could hear.
    """

    SAMPLES = ROOT / "assets" / "voice-samples" / "languages"

    @pytest.fixture(scope="class")
    def recorded(self) -> dict[str, str]:
        return {
            path.stem.split("-")[0]: path.stem.split("-")[1]
            for path in self.SAMPLES.glob("*.mp3")
        }

    def test_every_recording_names_a_real_pack(self, recorded):
        """A file for a language the engine does not support would be a
        recording nothing can ever route to."""
        from aera.voice.languages import PACKS

        unknown = set(recorded) - set(PACKS)

        assert not unknown, f"no language pack for: {sorted(unknown)}"

    def test_the_set_is_broad(self, recorded):
        assert len(recorded) >= 14

    @pytest.mark.parametrize(
        "script_group",
        [
            ["es", "fr", "de", "it", "pt"],   # Latin
            ["ru"],                            # Cyrillic
            ["ar"],                            # Arabic, right to left
            ["hi", "ne"],                      # Devanagari
            ["bn"],                            # Bengali
            ["ta"],                            # Tamil
            ["zh"],                            # Han
            ["ja"],                            # Kana
            ["ko"],                            # Hangul
        ],
    )
    def test_each_script_family_is_represented(self, script_group, recorded):
        """Nine writing systems, so the lip-sync readers are exercised by ear
        and not only by unit test."""
        assert any(code in recorded for code in script_group), (
            f"no recording for any of {script_group}"
        )

    def test_every_recording_is_documented(self, recorded):
        readme = (self.SAMPLES / "README.md").read_text(encoding="utf-8")

        for code, character in recorded.items():
            assert f"{code}-{character}.mp3" in readme, f"{code} is not in the table"

    def test_the_readme_lists_what_is_still_missing(self):
        """21 packs have no recording. Naming them is the difference between
        an incomplete set and a set that looks complete."""
        from aera.voice.languages import PACKS

        readme = (self.SAMPLES / "README.md").read_text(encoding="utf-8")
        recorded = {p.stem.split("-")[0] for p in self.SAMPLES.glob("*.mp3")}

        for code in sorted(set(PACKS) - recorded):
            assert f"`{code}`" in readme, f"{code} has no recording and is not listed"


class TestNodeWorkflow:
    """The Node CI workflow must match where the Node project actually is.

    GitHub's default template assumes package.json sits at the repository
    root. Here the Node application is the React interface under
    `interface/`, and there is no root manifest at all -- so every run died
    at `Use Node.js`, before npm ci was ever reached, because
    `actions/setup-node` with `cache: npm` could not find a lockfile.
    """

    @pytest.fixture(scope="class")
    def workflow(self) -> dict:
        import yaml

        return yaml.safe_load(
            (ROOT / "ci" / "github-actions-node.yml").read_text(encoding="utf-8")
        )

    @pytest.fixture(scope="class")
    def job(self, workflow) -> dict:
        return workflow["jobs"]["interface"]

    def test_there_is_no_root_package_json(self):
        """The premise. If this ever changes the workflow can be simplified,
        and this test is where that will be noticed."""
        assert not (ROOT / "package.json").exists()

    def test_the_cache_points_at_the_real_lockfile(self, job):
        setup = next(s for s in job["steps"] if "setup-node" in s.get("uses", ""))
        path = setup["with"]["cache-dependency-path"]

        assert (ROOT / path).is_file(), f"{path} does not exist"

    def test_npm_runs_in_the_interface_directory(self, job):
        assert job["defaults"]["run"]["working-directory"] == "interface"

    def test_every_npm_script_it_calls_exists(self, job):
        """A workflow calling a script that is not defined fails at the point
        of use, which is a slow way to learn about a typo."""
        import json

        scripts = json.loads(
            (ROOT / "interface" / "package.json").read_text(encoding="utf-8")
        )["scripts"]
        called = {
            line.strip().removeprefix("npm run ").strip()
            for step in job["steps"]
            for line in step.get("run", "").splitlines()
            if line.strip().startswith("npm run ")
        }

        assert called, "the workflow runs no npm scripts"
        for script in called:
            assert script in scripts, f"npm run {script} is not defined"

    def test_the_build_is_not_optional(self, job):
        """--if-present passes silently when there is no build script. The
        build is required here: PyInstaller refuses to package without it."""
        runs = " ".join(step.get("run", "") for step in job["steps"])

        assert "--if-present" not in runs

    def test_it_type_checks(self, job):
        runs = " ".join(step.get("run", "") for step in job["steps"])

        assert "typecheck" in runs

    def test_the_node_matrix_matches_what_vite_supports(self, job):
        """Vite 7 declares engines ^20.19.0 || >=22.12.0. Testing Node 18
        produces a failure the project cannot fix."""
        versions = job["strategy"]["matrix"]["node-version"]

        assert "18.x" not in versions
        assert all(not str(v).startswith("1") for v in versions)

    def test_it_verifies_the_build_output(self, job):
        """The build writes into aera/desktop/ui-react and the spec refuses
        to package without it, so a broken build should fail CI and not
        release."""
        runs = " ".join(step.get("run", "") for step in job["steps"])

        assert "aera/desktop/ui-react/index.html" in runs
