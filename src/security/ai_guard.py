"""AI Security (docs/21-SECURITY.md "AI Security").

Documented protections: Prompt Injection Detection, Unsafe Tool Calls,
Unauthorized Agent Actions, Context Isolation, Output Validation.

This module implements the first line of defense — heuristic prompt
injection detection and output validation — before requests reach the
Model Router. Model-based classification can replace the heuristics later
behind the same interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.logging.logger import get_logger

log = get_logger("security.ai")

# Prompt-injection heuristics: instruction-override and exfiltration patterns.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.I),
    re.compile(r"disregard\s+(your|the)\s+(system\s+)?(prompt|instructions|rules)", re.I),
    re.compile(r"you\s+are\s+now\s+(dan|jailbroken|unrestricted|developer\s+mode)", re.I),
    re.compile(r"reveal\s+(your|the)\s+(system\s+prompt|instructions|api\s+key|secret)", re.I),
    re.compile(r"(print|show|output|leak)\s+.{0,20}(api[_\s-]?key|password|secret|token)", re.I),
    re.compile(r"</?(system|assistant)>", re.I),  # role-tag smuggling
    re.compile(r"\bBEGIN\s+SYSTEM\s+PROMPT\b", re.I),
]

# Output validation: responses must never contain obvious secrets.
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),  # Google API keys
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),  # GitHub tokens
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
]


@dataclass
class ScanResult:
    safe: bool
    reason: str = ""


class AIGuard:
    """Screens prompts before inference and validates outputs after."""

    def scan_prompt(self, text: str) -> ScanResult:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                log.warning("prompt injection pattern matched: %s", pattern.pattern[:60])
                return ScanResult(safe=False, reason="possible prompt injection detected")
        return ScanResult(safe=True)

    def validate_output(self, text: str) -> ScanResult:
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                return ScanResult(safe=False, reason="response contains a secret-like string")
        return ScanResult(safe=True)

    def redact_output(self, text: str) -> str:
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text
