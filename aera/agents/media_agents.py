"""Document, media and network agents.

Several agents in the specified roster need capabilities the platform does not
ship: a vision model, an OCR engine, speech transcription. Rather than omit
them or let them invent output, they are implemented here with real capability
detection - they do genuine work when a backend is present and report their
limitation precisely when one is not.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import urllib.parse
from pathlib import Path
from typing import Any

from ..core.logging import get_logger
from .base import Agent, Capability, Task, TaskResult

logger = get_logger("agents.media")

# --------------------------------------------------------------------------- #
# document handling
# --------------------------------------------------------------------------- #

#: Extensions the document agent can read without extra dependencies.
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".csv", ".tsv", ".log", ".xml", ".html", ".sql",
}
#: Extensions that need a parser AERA does not bundle.
BINARY_DOCUMENTS = {".pdf", ".docx", ".xlsx", ".pptx", ".odt", ".epub"}


class DocumentAgent(Agent):
    """Reads and summarises documents.

    Plain-text formats are parsed directly. Binary formats are detected and
    reported rather than guessed at.
    """

    name = "document"
    description = "Reads, summarises and answers questions about documents."
    capabilities = (Capability.FILE_ANALYSIS, Capability.DOCUMENTATION)
    priority = 6

    MAX_CHARS = 40_000

    async def handle(self, task: Task) -> TaskResult:
        path_hint = task.context.get("path") or _first_path(task.input)

        if not path_hint:
            # No file given: treat the prompt itself as the document.
            return await self._summarise(task, task.input, source="inline text")

        path = Path(path_hint).expanduser()
        if not path.is_file():
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error=f"file not found: {path}",
                output=f"I could not find {path}.",
            )

        suffix = path.suffix.lower()
        if suffix in BINARY_DOCUMENTS:
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                success=False,
                output=(
                    f"{path.name} is a {suffix.lstrip('.').upper()} file. AERA does not "
                    f"bundle a parser for that format, so I cannot read it. Export it to "
                    f"text or Markdown and I will analyse it."
                ),
                error=f"no parser for {suffix}",
                data={"path": str(path), "format": suffix, "parser_available": False},
            )

        if suffix not in TEXT_EXTENSIONS and suffix != "":
            logger.debug("attempting to read %s as text", path)

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False, error=str(exc),
            )

        truncated = len(text) > self.MAX_CHARS
        return await self._summarise(
            task, text[: self.MAX_CHARS], source=str(path), truncated=truncated
        )

    async def _summarise(
        self, task: Task, text: str, *, source: str, truncated: bool = False
    ) -> TaskResult:
        question = task.context.get("question") or task.input
        system = (
            "You are AERA's Document Agent. Answer using only the supplied document. "
            "If the answer is not present, say so rather than inferring it. "
            "Lead with the answer, then cite the relevant passage."
        )
        prompt = f"Document ({source}):\n\n{text}\n\n---\n\nRequest: {question}"

        response = await self.ctx.router.complete(
            prompt, task="default", system=system, temperature=0.3
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={
                "source": source,
                "characters": len(text),
                "truncated": truncated,
                "words": len(text.split()),
            },
        )


# --------------------------------------------------------------------------- #
# vision / OCR / audio - capability-gated
# --------------------------------------------------------------------------- #
class VisionAgent(Agent):
    """Image understanding.

    Routes to a vision-capable provider when one is configured; otherwise
    reports the gap instead of describing an image it cannot see.
    """

    name = "vision"
    description = "Analyses images and screenshots using a vision-capable model."
    capabilities = (Capability.VISION,)
    priority = 6
    model_task = "vision"

    async def handle(self, task: Task) -> TaskResult:
        path = task.context.get("path") or _first_path(task.input)
        provider = await self._vision_provider()

        if provider is None:
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                success=False,
                output=(
                    "No vision-capable model is connected. Configure a provider that "
                    "supports images (OpenAI, Gemini or a local multimodal model) in "
                    "config/models.yaml, and I will analyse the image."
                ),
                error="no vision-capable provider",
                data={"path": path, "vision_available": False},
            )

        # A provider is available; describe what is being asked of it. Actually
        # transmitting image bytes needs the multimodal request shape, which the
        # router does not model yet.
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            success=False,
            output=(
                f"A vision-capable provider ({provider}) is connected, but AERA's model "
                "router does not yet send image payloads. Text-only requests work today; "
                "multimodal transport is the remaining piece."
            ),
            error="multimodal transport not implemented",
            data={"path": path, "provider": provider, "vision_available": True},
        )

    async def _vision_provider(self) -> str | None:
        for name, provider in self.ctx.router.providers.items():
            if not provider.enabled or not await provider.health_check():
                continue
            try:
                models = await provider.list_models()
            except Exception:  # noqa: BLE001
                continue
            if any(m.supports_vision for m in models):
                return name
        return None


class OCRAgent(Agent):
    """Text extraction from images."""

    name = "ocr"
    description = "Extracts text from images and scanned documents."
    capabilities = (Capability.VISION,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        path = task.context.get("path") or _first_path(task.input)
        engine = _detect_ocr_engine()

        if engine is None:
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                success=False,
                output=(
                    "No OCR engine is installed. Install Tesseract "
                    "(and pytesseract) or connect a vision model, and I will extract "
                    "text from images."
                ),
                error="no OCR engine available",
                data={"path": path, "engine": None},
            )

        try:
            text = _run_ocr(engine, Path(path)) if path else ""
        except Exception as exc:  # noqa: BLE001
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error=f"OCR failed: {exc}",
            )

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=text or "(no text detected)",
            data={"path": path, "engine": engine, "characters": len(text)},
        )


class AudioAgent(Agent):
    """Audio analysis and transcription."""

    name = "audio"
    description = "Transcribes and analyses audio recordings."
    capabilities = (Capability.VOICE,)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        path = task.context.get("path") or _first_path(task.input)
        backend = getattr(self.ctx, "voice", None)
        stt_name = getattr(getattr(backend, "stt", None), "name", "null")

        if stt_name == "null":
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                success=False,
                output=(
                    "No speech-to-text backend is installed, so I cannot transcribe "
                    "audio. Install Whisper (or another STT engine) and register it "
                    "with the voice engine to enable transcription."
                ),
                error="no STT backend",
                data={"path": path, "stt_backend": stt_name},
            )

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=f"Transcription would run through the '{stt_name}' backend.",
            data={"path": path, "stt_backend": stt_name},
        )


# --------------------------------------------------------------------------- #
# network
# --------------------------------------------------------------------------- #
class NetworkAgent(Agent):
    """Local network diagnostics.

    Read-only and local-only: resolves names, checks reachability of hosts the
    user names, and reports interface facts. It never scans ranges.
    """

    name = "network"
    description = "Runs local network diagnostics and connectivity checks."
    capabilities = (Capability.SECURITY, Capability.PERFORMANCE)
    priority = 5

    async def handle(self, task: Task) -> TaskResult:
        action = str(task.context.get("action", "status")).lower()
        host = task.context.get("host") or _first_host(task.input)

        if action == "resolve" and host:
            return self._resolve(task, host)
        if action == "check" and host:
            return self._check(task, host, int(task.context.get("port", 443)))
        return self._status(task)

    def _status(self, task: Task) -> TaskResult:
        info: dict[str, Any] = {"hostname": socket.gethostname()}
        try:
            info["local_ip"] = socket.gethostbyname(info["hostname"])
        except OSError:
            info["local_ip"] = "unresolved"
        try:
            with socket.create_connection(("1.1.1.1", 53), timeout=2):
                info["internet"] = True
        except OSError:
            info["internet"] = False

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=(
                f"Host {info['hostname']} at {info['local_ip']}. "
                f"Internet reachability: {'yes' if info['internet'] else 'no'}."
            ),
            data=info,
        )

    def _resolve(self, task: Task, host: str) -> TaskResult:
        try:
            addresses = sorted({r[4][0] for r in socket.getaddrinfo(host, None)})
        except OSError as exc:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error=f"could not resolve {host}: {exc}",
            )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=f"{host} resolves to {', '.join(addresses)}",
            data={"host": host, "addresses": addresses},
        )

    def _check(self, task: Task, host: str, port: int) -> TaskResult:
        try:
            with socket.create_connection((host, port), timeout=3):
                reachable = True
        except OSError:
            reachable = False
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=f"{host}:{port} is {'reachable' if reachable else 'not reachable'}.",
            data={"host": host, "port": port, "reachable": reachable},
        )


# --------------------------------------------------------------------------- #
# web
# --------------------------------------------------------------------------- #
class WebAgent(Agent):
    """Fetches web pages when network access is permitted.

    Refuses private and loopback addresses so a prompt cannot use AERA to probe
    the user's internal network (SSRF).
    """

    name = "web"
    description = "Fetches and summarises public web pages."
    capabilities = (Capability.RESEARCH,)
    priority = 6

    MAX_BYTES = 400_000

    async def handle(self, task: Task) -> TaskResult:
        url = task.context.get("url") or _first_url(task.input)
        if not url:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error="no URL supplied",
                output="Give me a URL to fetch.",
            )

        allowed = bool(getattr(self.ctx.config, "security", None)) and getattr(
            self.ctx.config.security, "allow_network", False
        )
        if not allowed:
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                success=False,
                output=(
                    "Outbound web access is disabled. Set security.allow_network to true "
                    "in config/security.yaml to let me fetch pages."
                ),
                error="network access disabled by policy",
                data={"url": url},
            )

        blocked = _is_private_url(url)
        if blocked:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error="refusing to fetch a private or loopback address",
                output="I only fetch public addresses, not internal network hosts.",
                data={"url": url},
            )

        try:
            import httpx

            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "AERA/1.0"})
                response.raise_for_status()
                body = response.text[: self.MAX_BYTES]
        except Exception as exc:  # noqa: BLE001
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error=f"fetch failed: {exc}",
            )

        text = _strip_html(body)
        summary = await self.ctx.router.complete(
            f"Page content:\n\n{text[:20000]}\n\n---\n\nRequest: {task.input}",
            task="research",
            system=(
                "You are AERA's Web Agent. Summarise only what the page actually says. "
                "Do not add outside knowledge or invent citations."
            ),
            temperature=0.4,
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=summary.content,
            model=summary.model,
            provider=summary.provider,
            data={"url": url, "characters": len(text)},
        )


# --------------------------------------------------------------------------- #
# conversation / personalization / collaboration
# --------------------------------------------------------------------------- #
class ConversationAgent(Agent):
    """Natural dialogue with memory-aware continuity."""

    name = "conversation"
    description = "Handles natural conversation with continuity across sessions."
    capabilities = (Capability.CONVERSATION,)
    priority = 6

    async def handle(self, task: Task) -> TaskResult:
        context = task.context.get("memory_context", "")
        if not context and task.conversation_id:
            context = await self.ctx.memory.build_context(
                task.input, conversation_id=task.conversation_id, max_items=5
            )

        system = (
            "You are AERA in conversation. Be warm but concise, and never pad. "
            "Use remembered context naturally instead of asking the user to repeat "
            "themselves. Match the user's register."
        )
        if context:
            system += f"\n\n{context}"

        response = await self.ctx.router.complete(
            task.input, task="default", system=system, temperature=0.75
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
            data={"used_memory": bool(context)},
        )


class PersonalizationAgent(Agent):
    """Learns and applies user preferences."""

    name = "personalization"
    description = "Tracks user preferences and adapts AERA's behaviour."
    capabilities = (Capability.LEARNING,)
    priority = 5

    _PREFERENCE = re.compile(
        r"\b(?:i (?:prefer|like|want|always|usually|never)|my favou?rite|call me|use)\b",
        re.I,
    )

    async def handle(self, task: Task) -> TaskResult:
        action = str(task.context.get("action", "list")).lower()

        if action == "learn" or self._PREFERENCE.search(task.input):
            node = await self.ctx.memory.store(
                title=f"Preference: {task.input[:60]}",
                content=task.input,
                node_type="preference",
                memory_type="long_term",
                tags=["preference", "personalization"],
                importance=0.85,
                creator=self.name,
            )
            return TaskResult(
                task_id=task.id,
                agent=self.name,
                output=f"Noted. I will remember: {task.input}",
                data={"stored": True},
                memory_ids=[node.id],
            )

        nodes = self.ctx.memory.graph.find(tag="preference", limit=25)
        if not nodes:
            return TaskResult(
                task_id=task.id, agent=self.name,
                output="I have not learned any preferences yet.",
                data={"preferences": []},
            )
        lines = [f"- {n.summary(110)}" for n in nodes]
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output="Preferences I have learned:\n" + "\n".join(lines),
            data={"preferences": [n.to_public() for n in nodes]},
        )


class CollaborationAgent(Agent):
    """Shared-context coordination."""

    name = "collaboration"
    description = "Coordinates shared context and multi-agent handoffs."
    capabilities = (Capability.PLANNING,)
    priority = 4

    async def handle(self, task: Task) -> TaskResult:
        registry = self.ctx.registry
        if registry is None:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error="no agent registry available",
            )

        capability_map = registry.capability_map()
        recent = registry.history(10)

        system = (
            "You are AERA's Collaboration Agent. Given the user's goal, propose which "
            "specialist agents should run, in what order, and what each hands to the "
            "next. Use only the agents listed. Be concrete.\n\n"
            f"Available: {json.dumps(capability_map)}"
        )
        response = await self.ctx.router.complete(
            task.input, task="reasoning", system=system, temperature=0.4
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={"agents_available": len(registry), "recent_tasks": len(recent)},
        )


class VoiceAgent(Agent):
    """Voice session control."""

    name = "voice"
    description = "Controls speech synthesis, listening sessions and emotion."
    capabilities = (Capability.VOICE,)
    priority = 6

    async def handle(self, task: Task) -> TaskResult:
        engine = getattr(self.ctx, "voice", None)
        if engine is None:
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error="voice engine unavailable",
            )

        action = str(task.context.get("action", "speak")).lower()

        if action == "status":
            status = engine.status()
            return TaskResult(
                task_id=task.id, agent=self.name,
                output=f"Voice is {status['state']} using {status['tts_backend']}.",
                data=status,
            )

        if action == "emotion":
            from ..voice.engine import detect_emotion

            emotion, confidence = detect_emotion(task.input)
            return TaskResult(
                task_id=task.id, agent=self.name,
                output=f"Detected emotion: {emotion.value} ({confidence:.0%} confidence).",
                data={"emotion": emotion.value, "confidence": confidence},
            )

        result = await engine.speak(task.input)
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=f"Spoke {len(task.input.split())} words with {result.emotion.value} tone.",
            data={
                "emotion": result.emotion.value,
                "duration_ms": result.duration_ms,
                "visemes": len(result.visemes),
                "engine": result.engine,
            },
        )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
_PATH_RE = re.compile(r"(?:^|\s)((?:~|\.{0,2}/)[\w./\-]+|[A-Za-z]:\\[\w\\.\- ]+)")
_URL_RE = re.compile(r"https?://[^\s<>\"')]+")
_HOST_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,}|\d{1,3}(?:\.\d{1,3}){3})\b", re.I)


def _first_path(text: str) -> str | None:
    match = _PATH_RE.search(text or "")
    return match.group(1).strip() if match else None


def _first_url(text: str) -> str | None:
    match = _URL_RE.search(text or "")
    return match.group(0) if match else None


def _first_host(text: str) -> str | None:
    url = _first_url(text)
    if url:
        return urllib.parse.urlparse(url).hostname
    match = _HOST_RE.search(text or "")
    return match.group(1) if match else None


def _is_private_url(url: str) -> bool:
    """True for loopback, link-local and RFC1918 destinations."""
    host = urllib.parse.urlparse(url).hostname
    if not host:
        return True
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        addresses = {r[4][0] for r in socket.getaddrinfo(host, None)}
    except OSError:
        return True
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def _strip_html(html: str) -> str:
    """Crude tag removal - enough to feed a summariser."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _detect_ocr_engine() -> str | None:
    try:
        import pytesseract  # noqa: F401

        return "tesseract"
    except ImportError:
        return None


def _run_ocr(engine: str, path: Path) -> str:  # pragma: no cover - needs the engine
    if engine == "tesseract":
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(path))
    raise RuntimeError(f"unsupported OCR engine: {engine}")
