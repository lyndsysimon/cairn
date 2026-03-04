from cairn.credentials.base import CredentialStore

__all__ = ["CredentialStore", "PostgresCredentialStore"]


def __getattr__(name: str):
    if name == "PostgresCredentialStore":
        from cairn.credentials.postgres import PostgresCredentialStore

        return PostgresCredentialStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
