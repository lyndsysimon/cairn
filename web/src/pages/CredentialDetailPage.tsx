import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  getCredential,
  updateCredential,
  deleteCredential,
} from "../api/client";
import type { Credential } from "../api/types";

export function CredentialDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [credential, setCredential] = useState<Credential | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [newValue, setNewValue] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getCredential(id)
      .then(setCredential)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSave() {
    if (!id || !newValue) return;
    try {
      const updated = await updateCredential(id, { value: newValue });
      setCredential(updated);
      setEditing(false);
      setNewValue("");
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDelete() {
    if (!id || !credential) return;
    if (!confirm(`Delete credential "${credential.credential_id}"?`)) return;
    try {
      await deleteCredential(id);
      navigate("/credentials");
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error && !credential) return <div className="error">{error}</div>;
  if (!credential) return <div className="error">Credential not found</div>;

  return (
    <>
      <div className="page-header">
        <h1>{credential.credential_id}</h1>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {!editing && (
            <>
              <button className="btn" onClick={() => setEditing(true)}>
                Rotate Value
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                Delete
              </button>
            </>
          )}
          <Link to="/credentials" className="btn">
            Back
          </Link>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="detail-section">
        <h2>Details</h2>
        <div className="detail-grid">
          <span className="detail-label">Credential ID</span>
          <span className="detail-value">
            <code>{credential.credential_id}</code>
          </span>
          <span className="detail-label">Store</span>
          <span className="detail-value">
            <code>{credential.store_name}</code>
          </span>
          <span className="detail-label">Created</span>
          <span className="detail-value">
            {new Date(credential.created_at).toLocaleString()}
          </span>
          <span className="detail-label">Updated</span>
          <span className="detail-value">
            {new Date(credential.updated_at).toLocaleString()}
          </span>
        </div>
      </div>

      {editing && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            handleSave();
          }}
        >
          <div className="form-group">
            <label className="form-label">New Value</label>
            <input
              className="form-input"
              type="password"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              required
              placeholder="Enter new secret value"
            />
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Update Value
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setEditing(false);
                setNewValue("");
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </>
  );
}
