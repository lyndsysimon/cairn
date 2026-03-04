"""PostgreSQL-backed credential store with Fernet encryption at rest."""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from cairn.credentials.encryption import decrypt_value, derive_key, encrypt_value
from cairn.models.credential import CredentialReference, CredentialValue


class PostgresCredentialStore:
    """CredentialStore implementation backed by PostgreSQL.

    All credential values are encrypted with Fernet before being written
    to the ``credentials.encrypted_value`` column and decrypted on read.
    """

    def __init__(self, pool: AsyncConnectionPool, encryption_key: str) -> None:
        self._pool = pool
        self._key = derive_key(encryption_key)

    @property
    def name(self) -> str:
        return "postgres"

    async def get_credential(self, ref: CredentialReference) -> CredentialValue:
        """Fetch and decrypt a single credential by its credential_id."""
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT encrypted_value FROM credentials"
                    " WHERE credential_id = %s AND store_name = %s",
                    (ref.credential_id, ref.store_name),
                )
                row = await cur.fetchone()

        if row is None:
            raise LookupError(
                f"Credential '{ref.credential_id}' not found in store '{ref.store_name}'"
            )

        plaintext = decrypt_value(bytes(row["encrypted_value"]), self._key)
        return CredentialValue(credential_id=ref.credential_id, value=plaintext)

    async def list_credentials(self) -> list[CredentialReference]:
        """List all credential references (without values)."""
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT credential_id, store_name FROM credentials"
                    " WHERE store_name = 'postgres'"
                    " ORDER BY credential_id ASC"
                )
                rows = await cur.fetchall()

        return [
            CredentialReference(
                credential_id=r["credential_id"],
                store_name=r["store_name"],
                env_var_name="",
            )
            for r in rows
        ]

    async def store_credential(self, ref: CredentialReference, value: str) -> None:
        """Encrypt and store a credential value."""
        encrypted = encrypt_value(value, self._key)
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO credentials"
                " (credential_id, encrypted_value, store_name)"
                " VALUES (%s, %s, %s)"
                " ON CONFLICT (credential_id) DO UPDATE"
                " SET encrypted_value = EXCLUDED.encrypted_value,"
                " updated_at = now()",
                (ref.credential_id, encrypted, ref.store_name),
            )
            await conn.commit()

    async def delete_credential(self, ref: CredentialReference) -> None:
        """Delete a credential by its credential_id."""
        async with self._pool.connection() as conn:
            await conn.execute(
                "DELETE FROM credentials WHERE credential_id = %s AND store_name = %s",
                (ref.credential_id, ref.store_name),
            )
            await conn.commit()
