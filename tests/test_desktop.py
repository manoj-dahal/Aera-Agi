"""Desktop application tests.

These exercise the kernel thread, the JS bridge and preference handling without
opening a window, so they run on headless CI exactly as they do on a desktop.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aera.desktop.app import DesktopApp
from aera.desktop.bridge import DesktopBridge
from aera.desktop.settings import DEFAULTS, DesktopSettings, app_data_dir


class FakeWindow:
    """Stands in for a pywebview window; records JS calls and dialog results."""

    def __init__(self, dialog_result=None) -> None:
        self.evaluated: list[str] = []
        self.dialog_result = dialog_result
        self.dialog_calls: list[tuple] = []
        self.destroyed = False
        self.width, self.height, self.x, self.y = 1200, 800, 10, 20

    def evaluate_js(self, code: str) -> None:
        self.evaluated.append(code)

    def create_file_dialog(self, dialog_type, **kwargs):
        self.dialog_calls.append((dialog_type, kwargs))
        return self.dialog_result

    def destroy(self) -> None:
        self.destroyed = True


@pytest.fixture
def app(config, tmp_path):
    """A started DesktopApp with an isolated preference file."""
    application = DesktopApp(config)
    application.settings = DesktopSettings(tmp_path / "prefs.json")
    application.start_kernel()
    try:
        yield application
    finally:
        application.stop_kernel()


@pytest.fixture
def bridge(app):
    window = FakeWindow()
    app.bridge.attach(window)
    app.window = window
    return app.bridge


class TestDesktopSettings:
    def test_defaults(self, tmp_path):
        settings = DesktopSettings(tmp_path / "p.json")
        assert settings.get("window_width") == DEFAULTS["window_width"]

    def test_round_trip(self, tmp_path):
        path = tmp_path / "p.json"
        DesktopSettings(path).set("window_width", 1600)
        assert DesktopSettings(path).get("window_width") == 1600

    def test_update_many(self, tmp_path):
        settings = DesktopSettings(tmp_path / "p.json")
        settings.update({"window_x": 5, "maximized": True})
        assert settings.get("window_x") == 5 and settings.get("maximized") is True

    def test_tolerates_corrupt_file(self, tmp_path):
        path = tmp_path / "p.json"
        path.write_text("{ not json", encoding="utf-8")
        assert DesktopSettings(path).get("window_width") == DEFAULTS["window_width"]

    def test_unknown_key_default(self, tmp_path):
        assert DesktopSettings(tmp_path / "p.json").get("nope", "fallback") == "fallback"

    def test_written_as_json(self, tmp_path):
        path = tmp_path / "p.json"
        DesktopSettings(path).set("last_view", "memory")
        assert json.loads(path.read_text())["last_view"] == "memory"

    def test_app_data_dir_exists(self):
        assert app_data_dir("AERA-Test").is_dir()


class TestKernelThread:
    def test_starts_and_reports_ready(self, app):
        assert app.kernel is not None and app.kernel.ready is True
        assert app.loop is not None and app.loop.is_running()

    def test_agents_are_running(self, app):
        assert app.kernel.registry.summary()["running"] > 0

    def test_stops_cleanly(self, config, tmp_path):
        application = DesktopApp(config)
        application.settings = DesktopSettings(tmp_path / "p.json")
        application.start_kernel()
        application.stop_kernel()
        assert not application.loop.is_running()

    def test_state_lives_in_app_data(self, config):
        # the default config redirects storage away from the repository
        default = DesktopApp._default_config()
        assert "AERA" in default.system.storage
        assert Path(default.security.secret_key_file).name == ".secret.key"


class TestBridgeConversation:
    def test_chat(self, bridge):
        res = bridge.chat("hello there", "t1")
        assert res["success"] is True
        assert res["data"]["output"] and res["data"]["conversation_id"] == "t1"

    def test_chat_routes_to_specialist(self, bridge):
        res = bridge.chat("write a python function to sort a list", "t2")
        assert res["data"]["agent"] == "coding"

    def test_chat_persists_memory(self, bridge, app):
        bridge.chat("remember: I prefer tabs", "t3")
        assert len(app.kernel.memory.conversation_history("t3")) == 2

    def test_stream_emits_tokens_and_done(self, bridge):
        import time

        window = bridge._window
        bridge.chat_stream("explain caching", "t4")

        for _ in range(200):
            if any("aeraOnDone" in call for call in window.evaluated):
                break
            time.sleep(0.05)

        assert any("aeraOnToken" in c for c in window.evaluated), "no tokens streamed"
        assert any("aeraOnDone" in c for c in window.evaluated), "stream never completed"

    def test_stream_payload_is_valid_json(self, bridge):
        import time

        window = bridge._window
        bridge.chat_stream("hi", "t5")
        for _ in range(200):
            if any("aeraOnDone" in c for c in window.evaluated):
                break
            time.sleep(0.05)

        call = next(c for c in window.evaluated if "aeraOnToken" in c)
        payload = call[call.index("(") + 1 : call.rindex(")")]
        assert "content" in json.loads(payload)


class TestBridgeWorkspace:
    def test_open_and_summarise(self, bridge, tmp_path):
        (tmp_path / "main.py").write_text("def run():\n    return 1\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")

        res = bridge.open_workspace(str(tmp_path))
        assert res["success"] is True and res["data"]["files"] == 2
        assert bridge.workspace_summary()["data"]["name"] == tmp_path.name

    def test_open_records_last_workspace(self, bridge, app, tmp_path):
        (tmp_path / "a.py").write_text("x=1")
        bridge.open_workspace(str(tmp_path))
        assert app.settings.get("last_workspace") == str(tmp_path.resolve())

    def test_open_missing_path(self, bridge):
        assert bridge.open_workspace("/no/such/place")["success"] is False

    def test_search(self, bridge, tmp_path):
        (tmp_path / "parser.py").write_text("def parse():\n    pass\n")
        bridge.open_workspace(str(tmp_path))
        results = bridge.workspace_search("parser")["data"]["results"]
        assert any("parser.py" in r["path"] for r in results)

    def test_read_file(self, bridge, tmp_path):
        (tmp_path / "a.py").write_text("value = 42\n")
        bridge.open_workspace(str(tmp_path))
        assert "value = 42" in bridge.read_workspace_file("a.py")["data"]["content"]

    def test_read_file_traversal_blocked(self, bridge, tmp_path):
        (tmp_path / "a.py").write_text("x=1")
        bridge.open_workspace(str(tmp_path))
        assert bridge.read_workspace_file("../../etc/passwd")["success"] is False

    def test_folder_dialog_opens_selection(self, app, tmp_path):
        (tmp_path / "a.py").write_text("x=1")
        window = FakeWindow(dialog_result=(str(tmp_path),))
        app.bridge.attach(window)
        res = app.bridge.open_folder_dialog()
        assert res["success"] is True and res["data"]["name"] == tmp_path.name
        assert window.dialog_calls, "the native dialog was never invoked"

    def test_folder_dialog_cancelled(self, app):
        app.bridge.attach(FakeWindow(dialog_result=None))
        res = app.bridge.open_folder_dialog()
        assert res["success"] is True and res["data"] is None

    def test_save_dialog_writes_file(self, app, tmp_path):
        target = tmp_path / "out.md"
        app.bridge.attach(FakeWindow(dialog_result=str(target)))
        res = app.bridge.save_file_dialog("out.md", "# exported\n")
        assert res["success"] is True
        assert target.read_text() == "# exported\n"

    def test_save_dialog_cancelled(self, app):
        app.bridge.attach(FakeWindow(dialog_result=None))
        assert app.bridge.save_file_dialog("x.md", "content")["data"] is None

    def test_reveal_missing_path(self, bridge):
        assert bridge.reveal_in_file_manager("/no/such/path")["success"] is False


class TestBridgeMemoryAndAgents:
    def test_memory_search(self, bridge):
        bridge.chat("postgres migration notes", "m1")
        results = bridge.memory_search("postgres")["data"]["results"]
        assert isinstance(results, list)

    def test_memory_list_and_stats(self, bridge):
        bridge.chat("hello", "m2")
        assert bridge.memory_list()["data"]["memories"]
        assert bridge.memory_stats()["data"]["nodes"] > 0

    def test_list_agents(self, bridge):
        data = bridge.list_agents()["data"]
        assert data["summary"]["total"] >= 15
        assert "coding" in data["capabilities"]["coding"]

    def test_system_status(self, bridge):
        assert bridge.system_status()["data"]["ready"] is True

    def test_provider_health(self, bridge):
        assert "builtin" in bridge.provider_health()["data"]

    def test_recent_events(self, bridge):
        bridge.chat("trigger some events", "e1")
        assert isinstance(bridge.recent_events()["data"]["events"], list)


class TestBridgeSettingsAndSecrets:
    def test_get_settings(self, bridge):
        data = bridge.get_settings()["data"]
        assert "settings" in data and "models" in data and "preferences" in data

    def test_set_preference(self, bridge, app):
        bridge.set_preference("last_view", "agents")
        assert app.settings.get("last_view") == "agents"

    def test_secret_round_trip_is_masked(self, bridge):
        bridge.set_secret("openai_api_key", "sk-supersecretvalue123")
        listed = bridge.list_secrets()["data"]["secrets"]
        assert "openai_api_key" in listed
        assert "supersecret" not in listed["openai_api_key"]

    def test_quit_destroys_window(self, app):
        window = FakeWindow()
        app.window = window
        app.bridge.attach(window)
        app.bridge.quit()
        assert window.destroyed is True


class TestBridgeResilience:
    def test_errors_return_envelope_not_raise(self, app):
        """A bridge call must never raise into the JS layer."""
        bridge = DesktopBridge(app)
        bridge.attach(FakeWindow())
        assert bridge.read_workspace_file("anything.py")["success"] is False

    def test_emit_without_window_is_safe(self, app):
        DesktopBridge(app)._emit("aeraOnToken", {"content": "x"})  # must not raise

    def test_chat_without_kernel_reports_error(self, config):
        application = DesktopApp(config)  # kernel never started
        bridge = DesktopBridge(application)
        bridge.attach(FakeWindow())
        assert bridge.chat("hello")["success"] is False


class TestUIAssets:
    """The packaged app loads these from disk; a missing file is a broken build."""

    @pytest.mark.parametrize("name", ["index.html", "style.css", "app.js"])
    def test_asset_present(self, name):
        from aera.desktop.app import UI_DIR

        assert (UI_DIR / name).is_file(), f"missing desktop asset: {name}"

    def test_html_references_local_assets_only(self):
        from aera.desktop.app import UI_DIR

        html = (UI_DIR / "index.html").read_text()
        # A desktop app must not depend on a network round trip to render.
        assert "http://" not in html and "https://" not in html

    def test_js_uses_the_native_bridge(self):
        from aera.desktop.app import UI_DIR

        js = (UI_DIR / "app.js").read_text()
        assert "pywebview.api" in js
        assert "fetch(" not in js, "desktop UI must not use HTTP"
