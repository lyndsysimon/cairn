from collections.abc import AsyncGenerator

from psycopg import AsyncConnection

from cairn.config import settings
from cairn.credentials.postgres import PostgresCredentialStore
from cairn.db.connection import get_pool
from cairn.db.repositories import provider_repo
from cairn.execution.service import ExecutionService
from cairn.llm.anthropic import AnthropicClient
from cairn.llm.base import LLMClient
from cairn.llm.openrouter import OpenRouterClient
from cairn.orchestration.service import OrchestrationService
from cairn.orchestration.tools import AgentToolRegistry
from cairn.runtime.docker import DockerRuntimeProvider
from cairn.security import (
    CredentialLeakDetector,
    PromptInjectionDetector,
    SecurityPipeline,
)


async def get_db_connection() -> AsyncGenerator[AsyncConnection]:
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn


def _get_security_pipeline() -> SecurityPipeline:
    return SecurityPipeline(
        middlewares=[CredentialLeakDetector(), PromptInjectionDetector()],
        registry={
            "credential_leak_detector": CredentialLeakDetector,
            "prompt_injection_detector": PromptInjectionDetector,
        },
    )


def get_credential_store() -> PostgresCredentialStore | None:
    if settings.encryption_key:
        return PostgresCredentialStore(get_pool(), settings.encryption_key)
    return None


def get_execution_service() -> ExecutionService:
    runtime = DockerRuntimeProvider()
    security = _get_security_pipeline()
    credential_store = get_credential_store()
    return ExecutionService(runtime=runtime, security=security, credential_store=credential_store)


async def _llm_client_factory(provider_name: str, conn: AsyncConnection) -> LLMClient:
    """Create an LLM client for the given model provider name.

    Looks up the provider in the database to get the API key credential,
    resolves the key, and returns the appropriate client.
    """
    providers = await provider_repo.list_all(conn, enabled_only=True)
    provider = next((p for p in providers if p.name == provider_name), None)
    if provider is None:
        raise ValueError(f"Model provider {provider_name!r} not found or not enabled")

    # Resolve the API key
    api_key = ""
    if provider.api_key_credential_id:
        cred_store = get_credential_store()
        if cred_store is not None:
            from cairn.models.credential import CredentialReference

            ref = CredentialReference(
                store_name="postgres",
                credential_id=provider.api_key_credential_id,
                env_var_name="",
            )
            cred_val = await cred_store.get_credential(ref)
            api_key = cred_val.value

    if provider.provider_type == "anthropic":
        return AnthropicClient(api_key=api_key, base_url=provider.api_base_url)
    elif provider.provider_type == "openrouter":
        return OpenRouterClient(api_key=api_key, base_url=provider.api_base_url)

    raise ValueError(f"Unsupported provider type: {provider.provider_type}")


def get_orchestration_service() -> OrchestrationService:
    execution_service = get_execution_service()
    security = _get_security_pipeline()
    credential_store = get_credential_store()
    tool_registry = AgentToolRegistry(execution_service)
    return OrchestrationService(
        llm_client_factory=_llm_client_factory,
        tool_registry=tool_registry,
        security=security,
        credential_store=credential_store,
    )
