"""Tests for the PostgresCredentialStore.

Uses a mock connection pool to avoid needing a real database.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cairn.credentials.encryption import derive_key, encrypt_value
from cairn.credentials.postgres import PostgresCredentialStore
from cairn.models.credential import CredentialReference, CredentialValue


@pytest.fixture
def encryption_key():
    return "test-passphrase"


@pytest.fixture
def fernet_key(encryption_key):
    return derive_key(encryption_key)


def _make_pool(rows=None):
    """Create a mock AsyncConnectionPool that yields a mock connection."""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=rows[0] if rows else None)
    cursor.fetchall = AsyncMock(return_value=rows or [])

    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.commit = AsyncMock()

    # Support `async with conn.cursor(row_factory=...) as cur:`
    cursor_ctx = MagicMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=False)
    conn.cursor = MagicMock(return_value=cursor_ctx)

    # Support `async with pool.connection() as conn:`
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.connection = MagicMock(return_value=conn_ctx)

    return pool, conn, cursor


class TestGetCredential:
    @pytest.mark.asyncio
    async def test_returns_decrypted_value(self, encryption_key, fernet_key):
        encrypted = encrypt_value("my-api-key", fernet_key)
        pool, conn, cursor = _make_pool(rows=[{"encrypted_value": encrypted}])
        store = PostgresCredentialStore(pool, encryption_key)
        ref = CredentialReference(
            credential_id="api-key",
            store_name="postgres",
            env_var_name="API_KEY",
        )

        result = await store.get_credential(ref)

        assert isinstance(result, CredentialValue)
        assert result.credential_id == "api-key"
        assert result.value == "my-api-key"

    @pytest.mark.asyncio
    async def test_not_found_raises(self, encryption_key):
        pool, conn, cursor = _make_pool(rows=[])
        cursor.fetchone = AsyncMock(return_value=None)
        store = PostgresCredentialStore(pool, encryption_key)
        ref = CredentialReference(
            credential_id="missing",
            store_name="postgres",
            env_var_name="X",
        )

        with pytest.raises(LookupError, match="not found"):
            await store.get_credential(ref)


class TestStoreCredential:
    @pytest.mark.asyncio
    async def test_encrypts_before_storing(self, encryption_key):
        pool, conn, cursor = _make_pool()
        store = PostgresCredentialStore(pool, encryption_key)
        ref = CredentialReference(
            credential_id="new-key",
            store_name="postgres",
            env_var_name="NEW_KEY",
        )

        await store.store_credential(ref, "secret-value")

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args[0]
        # Second positional arg is the params tuple.
        params = call_args[1]
        # The credential_id should be in the params.
        assert params[0] == "new-key"
        # The encrypted value should NOT be the plaintext.
        assert params[1] != b"secret-value"
        assert params[1] != "secret-value"
        conn.commit.assert_called_once()


class TestDeleteCredential:
    @pytest.mark.asyncio
    async def test_deletes_by_credential_id(self, encryption_key):
        pool, conn, cursor = _make_pool()
        store = PostgresCredentialStore(pool, encryption_key)
        ref = CredentialReference(
            credential_id="old-key",
            store_name="postgres",
            env_var_name="OLD",
        )

        await store.delete_credential(ref)

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args[0]
        assert "old-key" in call_args[1]
        conn.commit.assert_called_once()


class TestListCredentials:
    @pytest.mark.asyncio
    async def test_returns_references(self, encryption_key):
        pool, conn, cursor = _make_pool(
            rows=[
                {"credential_id": "key-a", "store_name": "postgres"},
                {"credential_id": "key-b", "store_name": "postgres"},
            ]
        )
        store = PostgresCredentialStore(pool, encryption_key)

        refs = await store.list_credentials()

        assert len(refs) == 2
        assert refs[0].credential_id == "key-a"
        assert refs[1].credential_id == "key-b"


class TestStoreName:
    def test_name_property(self):
        pool = MagicMock()
        store = PostgresCredentialStore(pool, "key")
        assert store.name == "postgres"
