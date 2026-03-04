from cairn.orchestration.tools import AgentToolRegistry

__all__ = [
    "AgentToolRegistry",
    "OrchestrationService",
]


def __getattr__(name: str):
    if name == "OrchestrationService":
        from cairn.orchestration.service import OrchestrationService

        return OrchestrationService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
