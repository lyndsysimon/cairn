"""Credential leak detection middleware.

Scans outbound prompts for credential values that should never appear
in text sent to an LLM.  Checks for both literal and base64-encoded
forms of each credential.
"""

import base64

_REDACTED = "[REDACTED]"

# Minimum credential length to scan for.  Anything shorter causes too
# many false-positive matches on common words / substrings.
_MIN_CREDENTIAL_LEN = 4


class CredentialLeakDetector:
    """Detects and redacts credential values in outbound prompts."""

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        if not credential_values or not prompt:
            return prompt

        result = prompt
        # Process longer values first so that a shorter credential that
        # happens to be a substring of a longer one doesn't cause a
        # partial redaction that hides the longer match.
        for value in sorted(credential_values, key=len, reverse=True):
            if len(value) < _MIN_CREDENTIAL_LEN:
                continue
            result = _redact_literal(result, value)
            result = _redact_base64(result, value)

        return result

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        return content, []


def _redact_literal(text: str, value: str) -> str:
    """Replace all literal occurrences of *value* (case-sensitive)."""
    return text.replace(value, _REDACTED)


def _redact_base64(text: str, value: str) -> str:
    """Replace standard and URL-safe base64 encodings of *value*."""
    encoded_bytes = value.encode()

    for encoder in (base64.b64encode, base64.urlsafe_b64encode):
        encoded = encoder(encoded_bytes).decode()
        # Also try without trailing padding (commonly stripped).
        encoded_stripped = encoded.rstrip("=")
        # Escape for safe use in a regex (base64 is mostly safe, but be
        # defensive about '+' and other characters).
        for variant in (encoded, encoded_stripped):
            if variant and variant in text:
                text = text.replace(variant, _REDACTED)

    return text
