from typing import Protocol


class SecurityInspector(Protocol):
    """Interface for the security middleware layer.

    Inspects outbound prompts for secret leakage and inbound responses
    for prompt injection before they enter agent context.
    """

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        """Scan an outbound prompt for leaked credentials. Returns sanitized prompt."""
        ...

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        """Scan inbound content for prompt injection. Returns (sanitized content, warnings)."""
        ...


class PassthroughInspector:
    """No-op implementation for initial development."""

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        return prompt

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        return content, []
