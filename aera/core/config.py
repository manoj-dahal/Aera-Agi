# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Configuration system.

Implements the layered loader described in ``docs/config/System-Config.md``:

    defaults  ->  config/*.yaml  ->  environment variables (AERA_*)

Every section is a validated pydantic model, so a malformed config fails fast
at startup with a precise message rather than at first use.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydValidationError

from .errors import ConfigError

# --------------------------------------------------------------------------- #
# section models
# --------------------------------------------------------------------------- #


class SystemSection(BaseModel):
    name: str = "AERA"
    version: str = "1.0.0"
    environment: Literal["development", "testing", "production", "enterprise"] = "development"
    debug: bool = False
    language: str = "en"
    timezone: str = "UTC"
    auto_update: bool = True
    workspace: str = "~/Workspace"
    logs: str = "./logs"
    cache: str = "./cache"
    temp: str = "./temp"
    storage: str = "./storage"


class ApiSection(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 100
    auth_enabled: bool = False
    api_keys: list[str] = Field(default_factory=list)
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_seconds: int = 86400

    @field_validator("port")
    @classmethod
    def _valid_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"port must be 1-65535, got {v}")
        return v


class LocalModelSection(BaseModel):
    enabled: bool = True
    provider: str = "ollama"
    model: str = "llama3"
    endpoint: str = "http://localhost:11434"
    gpu: bool = True
    context: int = 32768


class EmbeddingSection(BaseModel):
    model: str = "text-embedding"
    dimensions: int = 256


class ModelsSection(BaseModel):
    """Task -> provider routing table (``docs/config/Models.md``)."""

    default: str = "local"
    reasoning: str = "local"
    coding: str = "local"
    research: str = "local"
    vision: str = "local"
    routing_mode: Literal[
        "automatic", "local_first", "cloud_first", "manual", "performance", "privacy", "offline"
    ] = "local_first"
    local: LocalModelSection = Field(default_factory=LocalModelSection)
    embedding: EmbeddingSection = Field(default_factory=EmbeddingSection)
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)


class MemorySection(BaseModel):
    enabled: bool = True
    graph: bool = True
    vector_database: str = "internal"
    embeddings: str = "text-embedding"
    long_term: bool = True
    short_term: bool = True
    semantic: bool = True
    episodic: bool = True
    procedural: bool = True
    auto_cleanup: bool = True
    short_term_ttl_seconds: int = 3600
    short_term_capacity: int = 200
    recall_limit: int = 10
    importance_threshold: float = 0.25


class AgentsSection(BaseModel):
    """Enable/disable flags per agent (``docs/config/Agents.md``)."""

    core: bool = True
    memory: bool = True
    coding: bool = True
    reasoning: bool = True
    planning: bool = True
    workspace: bool = True
    security: bool = True
    automation: bool = True
    performance: bool = True
    notification: bool = True
    research: bool = True
    writing: bool = True
    terminal: bool = False
    git: bool = True
    vision: bool = True
    voice: bool = True
    translation: bool = True
    ethical_hacking: bool = True
    document: bool = True
    network: bool = True
    conversation: bool = True
    personalization: bool = True
    collaboration: bool = True
    web: bool = False
    audio: bool = False
    device: bool = True
    learning: bool = True
    update: bool = True
    monitoring: bool = True
    max_concurrent_tasks: int = 8
    task_timeout_seconds: int = 120

    def enabled_agents(self) -> set[str]:
        skip = {"max_concurrent_tasks", "task_timeout_seconds"}
        return {k for k, v in self.model_dump().items() if k not in skip and v is True}


class VoiceSection(BaseModel):
    enabled: bool = True
    wake_word: str = "AERA"
    language: str = "en"
    #: Retained for compatibility. Expression is always active: a flat
    #: delivery made AERA sound broken rather than neutral.
    emotion: bool = True
    hologram_sync: bool = True
    noise_reduction: bool = True
    echo_cancellation: bool = True
    speech_speed: float = 1.0
    pitch: float = 1.0
    volume: int = 100
    #: Voice persona: anime-g, anime-b or aera. Follows the active avatar
    #: variant when persona_follows_avatar is on.
    persona: str = "aera"
    persona_follows_avatar: bool = True
    #: Write WAV files for synthesised speech. Off by default: the bundled
    #: synthesiser is a vocoder, not a speech engine.
    write_audio: bool = False
    #: TTS backend: "auto" picks the best that can actually run, or name one
    #: of piper / system / persona explicitly.
    tts_backend: str = "auto"
    #: Path to a Piper .onnx voice model. Needed for real speech; without it
    #: AERA falls back and says so.
    piper_model: str | None = None


class WorkspaceSection(BaseModel):
    default: str = "~/Projects"
    auto_index: bool = True
    watch_changes: bool = True
    backup: bool = True
    git_detection: bool = True
    docker_detection: bool = True
    cache: bool = True
    max_file_size_bytes: int = 2_000_000
    index_extensions: list[str] = Field(
        default_factory=lambda: [
            ".py", ".dart", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
            ".kt", ".swift", ".c", ".h", ".cpp", ".hpp", ".cs", ".php", ".rb",
            ".sh", ".sql", ".md", ".yaml", ".yml", ".json", ".toml", ".txt",
        ]
    )
    ignore_dirs: list[str] = Field(
        default_factory=lambda: [
            ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
            "build", "target", ".idea", ".dart_tool", ".mypy_cache", ".pytest_cache",
        ]
    )


class SecuritySection(BaseModel):
    zero_trust: bool = True
    encrypt_secrets: bool = True
    audit_log: bool = True
    sandbox_plugins: bool = True
    allow_terminal: bool = False
    allow_network: bool = False
    #: Reading container state is always allowed; starting, stopping and
    #: removing them is not, matching the terminal's default-deny posture.
    allow_docker_control: bool = False
    terminal_allowlist: list[str] = Field(
        default_factory=lambda: ["ls", "cat", "pwd", "echo", "git", "python3", "node"]
    )
    secret_key_file: str = "./storage/.secret.key"
    max_upload_bytes: int = 20_000_000


class SettingsSection(BaseModel):
    theme: str = "dark"
    language: str = "en"
    animations: bool = True
    hologram: bool = True
    dashboard: bool = True
    startup: bool = True
    telemetry: bool = False
    notifications: bool = True


class DatabaseSection(BaseModel):
    driver: Literal["sqlite", "postgres"] = "sqlite"
    path: str = "./storage/aera.db"
    dsn: str | None = None
    pool_size: int = 5
    backup_enabled: bool = True


class LoggingSection(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_format: bool = False
    file: str | None = None


class AeraConfig(BaseModel):
    """Root configuration object."""

    system: SystemSection = Field(default_factory=SystemSection)
    api: ApiSection = Field(default_factory=ApiSection)
    models: ModelsSection = Field(default_factory=ModelsSection)
    memory: MemorySection = Field(default_factory=MemorySection)
    agents: AgentsSection = Field(default_factory=AgentsSection)
    voice: VoiceSection = Field(default_factory=VoiceSection)
    workspace: WorkspaceSection = Field(default_factory=WorkspaceSection)
    security: SecuritySection = Field(default_factory=SecuritySection)
    settings: SettingsSection = Field(default_factory=SettingsSection)
    database: DatabaseSection = Field(default_factory=DatabaseSection)
    logging: LoggingSection = Field(default_factory=LoggingSection)

    # -- derived paths ---------------------------------------------------- #
    def path_for(self, value: str) -> Path:
        return Path(os.path.expandvars(value)).expanduser().resolve()

    @property
    def storage_dir(self) -> Path:
        return self.path_for(self.system.storage)

    @property
    def logs_dir(self) -> Path:
        return self.path_for(self.system.logs)

    @property
    def cache_dir(self) -> Path:
        return self.path_for(self.system.cache)

    @property
    def temp_dir(self) -> Path:
        return self.path_for(self.system.temp)

    def ensure_dirs(self) -> None:
        for p in (self.storage_dir, self.logs_dir, self.cache_dir, self.temp_dir):
            p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# loader
# --------------------------------------------------------------------------- #

_SECTION_FILES = {
    "system": "system.yaml",
    "api": "api.yaml",
    "models": "models.yaml",
    "memory": "memory.yaml",
    "agents": "agents.yaml",
    "voice": "voice.yaml",
    "workspace": "workspace.yaml",
    "security": "security.yaml",
    "settings": "settings.yaml",
    "database": "database.yaml",
    "logging": "logging.yaml",
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level")
    return data


def _coerce(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "none", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if "," in raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return raw


def _env_overrides(env: dict[str, str]) -> dict:
    """Map ``AERA_API__PORT=9000`` -> ``{"api": {"port": 9000}}``."""
    out: dict[str, Any] = {}
    for key, value in env.items():
        if not key.startswith("AERA_") or key == "AERA_CONFIG_DIR":
            continue
        path = key[len("AERA_"):].lower().split("__")
        cursor = out
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = _coerce(value)
    return out


def load_config(
    config_dir: str | Path | None = None,
    *,
    overrides: dict | None = None,
    use_env: bool = True,
) -> AeraConfig:
    """Load, merge and validate the configuration.

    Precedence (lowest to highest): model defaults, ``<config_dir>/*.yaml``,
    ``AERA_*`` environment variables, then explicit ``overrides``.
    """
    if config_dir is None:
        config_dir = os.environ.get("AERA_CONFIG_DIR", "config")
    cdir = Path(config_dir).expanduser()

    merged: dict[str, Any] = {}

    # A single aera.yaml may hold every section, useful for containers.
    combined = _read_yaml(cdir / "aera.yaml")
    if combined:
        merged = _deep_merge(merged, combined)

    for section, filename in _SECTION_FILES.items():
        data = _read_yaml(cdir / filename)
        if not data:
            continue
        # files may be written either flat or nested under the section name
        payload = data.get(section, data) if isinstance(data.get(section), dict) else data
        merged = _deep_merge(merged, {section: payload})

    if use_env:
        merged = _deep_merge(merged, _env_overrides(dict(os.environ)))
    if overrides:
        merged = _deep_merge(merged, overrides)

    try:
        return AeraConfig(**merged)
    except PydValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigError(f"configuration validation failed: {problems}") from exc


_active: AeraConfig | None = None


def get_config() -> AeraConfig:
    """Return the process-wide config, loading it on first use."""
    global _active
    if _active is None:
        _active = load_config()
    return _active


def set_config(config: AeraConfig) -> None:
    global _active
    _active = config


def reset_config() -> None:
    global _active
    _active = None
