from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from cairn.models.agent import AgentDefinition


class SecurityMiddleware(Protocol):
    """Interface for a single security middleware layer.

    Each middleware inspects outbound prompts for secret leakage and/or
    inbound responses for prompt injection.  Implementations that only
    care about one direction should pass through the other unchanged.
    """

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        """Scan an outbound prompt for leaked credentials. Returns sanitized prompt."""
        ...

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        """Scan inbound content for prompt injection. Returns (sanitized content, warnings)."""
        ...


class SecurityPipeline:
    """Chains zero or more :class:`SecurityMiddleware` instances.

    Platform-level middlewares are supplied at construction time.
    Per-agent middlewares are resolved by name from a registry via
    :meth:`for_agent`, which returns a *new* pipeline combining both.

    ``SecurityPipeline`` itself satisfies the :class:`SecurityMiddleware`
    protocol, so it can be used anywhere a single middleware is expected.
    """

    def __init__(
        self,
        middlewares: list[SecurityMiddleware] | None = None,
        registry: dict[str, type] | None = None,
    ) -> None:
        self._middlewares: list[SecurityMiddleware] = list(middlewares or [])
        self._registry: dict[str, type] = dict(registry or {})

    # -- Registry management --------------------------------------------------

    def register(self, name: str, cls: type) -> None:
        """Register a middleware class under *name* for per-agent resolution."""
        self._registry[name] = cls

    # -- Per-agent composition ------------------------------------------------

    def for_agent(self, agent: AgentDefinition) -> SecurityPipeline:
        """Return a new pipeline combining platform + agent middlewares.

        Agent-specific middleware names are looked up in the registry and
        appended after the platform middlewares.
        """
        agent_middlewares: list[SecurityMiddleware] = []
        for name in agent.security_middlewares:
            if name not in self._registry:
                raise ValueError(f"Unknown security middleware: {name!r}")
            agent_middlewares.append(self._registry[name]())
        return SecurityPipeline(
            middlewares=self._middlewares + agent_middlewares,
            registry=self._registry,
        )

    # -- SecurityMiddleware protocol ------------------------------------------

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        result = prompt
        for mw in self._middlewares:
            result = await mw.inspect_outbound(result, credential_values)
        return result

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        result = content
        all_warnings: list[str] = []
        for mw in self._middlewares:
            result, warnings = await mw.inspect_inbound(result)
            all_warnings.extend(warnings)
        return result, all_warnings
