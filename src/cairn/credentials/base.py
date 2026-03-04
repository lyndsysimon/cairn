from typing import Protocol

from cairn.models.credential import CredentialReference, CredentialValue


class CredentialStore(Protocol):
    """Interface for credential storage and retrieval.

    Credential stores manage secrets (API keys, tokens, service accounts).
    The platform resolves CredentialReferences to CredentialValues at
    agent execution time, injecting them into the runtime environment.
    """

    @property
    def name(self) -> str: ...

    async def get_credential(self, ref: CredentialReference) -> CredentialValue: ...

    async def list_credentials(self) -> list[CredentialReference]: ...

    async def store_credential(self, ref: CredentialReference, value: str) -> None: ...

    async def delete_credential(self, ref: CredentialReference) -> None: ...
