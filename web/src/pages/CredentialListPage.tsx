import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listCredentials, deleteCredential } from "../api/client";
import type { Credential } from "../api/types";

const STORE_NAMES = ["postgres", "bitwarden"];

export function CredentialListPage() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [storeFilter, setStoreFilter] = useState<string>("");

  useEffect(() => {
    loadCredentials(storeFilter || undefined);
  }, [storeFilter]);

  function loadCredentials(storeName?: string) {
    setLoading(true);
    listCredentials(storeName)
      .then((data) => setCredentials(data.credentials))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }

  async function handleDelete(cred: Credential) {
    if (!confirm(`Delete credential "${cred.credential_id}"?`)) return;
    try {
      await deleteCredential(cred.id);
      setCredentials((prev) => prev.filter((c) => c.id !== cred.id));
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <>
      <div className="page-header">
        <h1>Credentials</h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select
            className="form-select"
            value={storeFilter}
            onChange={(e) => setStoreFilter(e.target.value)}
            style={{ width: "auto", minWidth: "140px" }}
          >
            <option value="">All stores</option>
            {STORE_NAMES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <Link to="/credentials/new" className="btn btn-primary">
            Add Credential
          </Link>
        </div>
      </div>

      {credentials.length === 0 ? (
        <div className="empty-state">
          <p>No credentials configured yet.</p>
          <Link to="/credentials/new" className="btn btn-primary">
            Add Credential
          </Link>
        </div>
      ) : (
        <table className="agent-table">
          <thead>
            <tr>
              <th>Credential ID</th>
              <th>Store</th>
              <th>Created</th>
              <th>Updated</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {credentials.map((cred) => (
              <tr key={cred.id}>
                <td>
                  <Link
                    to={`/credentials/${cred.id}`}
                    className="agent-name-link"
                  >
                    {cred.credential_id}
                  </Link>
                </td>
                <td>
                  <code>{cred.store_name}</code>
                </td>
                <td>{new Date(cred.created_at).toLocaleDateString()}</td>
                <td>{new Date(cred.updated_at).toLocaleDateString()}</td>
                <td>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(cred)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
