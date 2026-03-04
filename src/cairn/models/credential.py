from pydantic import BaseModel


class CredentialReference(BaseModel):
    """Reference to a credential in a credential store. Does not contain the secret value."""

    store_name: str
    credential_id: str
    env_var_name: str


class CredentialValue(BaseModel):
    """Resolved credential with actual value. Internal only — never exposed in API responses."""

    credential_id: str
    value: str
