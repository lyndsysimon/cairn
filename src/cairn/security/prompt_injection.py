"""Prompt injection detection middleware.

Scans inbound content (agent output / external data) for patterns that
suggest prompt injection — attempts to override system instructions,
manipulate roles, invoke tools, or exfiltrate data.

This is defence-in-depth: the middleware returns warnings but does
**not** modify or block the content.
"""

import re
from typing import NamedTuple


class _PatternDef(NamedTuple):
    category: str
    pattern: re.Pattern[str]

_PATTERNS: list[_PatternDef] = [
    # -- System prompt override ------------------------------------------------
    _PatternDef(
        "system_prompt_override",
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    ),
    _PatternDef(
        "system_prompt_override",
        re.compile(r"disregard\s+(all\s+)?prior\s+(instructions|context)", re.IGNORECASE),
    ),
    _PatternDef(
        "system_prompt_override",
        re.compile(r"forget\s+(all\s+)?(your\s+)?instructions", re.IGNORECASE),
    ),
    _PatternDef(
        "system_prompt_override",
        re.compile(r"new\s+system\s+prompt", re.IGNORECASE),
    ),
    _PatternDef(
        "system_prompt_override",
        re.compile(r"you\s+are\s+now\b", re.IGNORECASE),
    ),
    # -- Role / delimiter manipulation -----------------------------------------
    _PatternDef(
        "role_manipulation",
        re.compile(r"^SYSTEM\s*:", re.MULTILINE),
    ),
    _PatternDef(
        "role_manipulation",
        re.compile(r"^ASSISTANT\s*:", re.MULTILINE),
    ),
    _PatternDef(
        "role_manipulation",
        re.compile(r"###\s*Instruction", re.IGNORECASE),
    ),
    _PatternDef(
        "role_manipulation",
        re.compile(r"\[INST\]", re.IGNORECASE),
    ),
    _PatternDef(
        "role_manipulation",
        re.compile(r"<<\s*SYS\s*>>", re.IGNORECASE),
    ),
    # -- Tool / function call abuse --------------------------------------------
    _PatternDef(
        "tool_abuse",
        re.compile(r'"function_call"\s*:', re.IGNORECASE),
    ),
    _PatternDef(
        "tool_abuse",
        re.compile(r'"tool_use"\s*:', re.IGNORECASE),
    ),
    _PatternDef(
        "tool_abuse",
        re.compile(r'"tool_calls"\s*:', re.IGNORECASE),
    ),
    _PatternDef(
        "tool_abuse",
        re.compile(r'"type"\s*:\s*"function"', re.IGNORECASE),
    ),
    # -- Data exfiltration attempts --------------------------------------------
    _PatternDef(
        "data_exfiltration",
        re.compile(r"send\s+to\s+https?://", re.IGNORECASE),
    ),
    _PatternDef(
        "data_exfiltration",
        re.compile(r"\bcurl\s+", re.IGNORECASE),
    ),
    _PatternDef(
        "data_exfiltration",
        re.compile(r"\bwget\s+", re.IGNORECASE),
    ),
    _PatternDef(
        "data_exfiltration",
        re.compile(r"\bfetch\s*\(", re.IGNORECASE),
    ),
    # -- Delimiter injection ---------------------------------------------------
    _PatternDef(
        "delimiter_injection",
        re.compile(r"<\|im_start\|>", re.IGNORECASE),
    ),
    _PatternDef(
        "delimiter_injection",
        re.compile(r"<\|im_end\|>", re.IGNORECASE),
    ),
    _PatternDef(
        "delimiter_injection",
        re.compile(r"<\|endoftext\|>", re.IGNORECASE),
    ),
]


class PromptInjectionDetector:
    """Detects prompt injection patterns in inbound content."""

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        return prompt

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        if not content:
            return content, []

        seen_categories: set[str] = set()
        warnings: list[str] = []

        for pdef in _PATTERNS:
            if pdef.category in seen_categories:
                continue
            if pdef.pattern.search(content):
                seen_categories.add(pdef.category)
                warnings.append(
                    f"Possible prompt injection detected ({pdef.category})"
                )

        return content, warnings
