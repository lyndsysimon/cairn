import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { createCredential } from "../api/client";

export function CreateCredentialPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [credentialId, setCredentialId] = useState("");
  const [storeName, setStoreName] = useState("postgres");
  const [value, setValue] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const cred = await createCredential({
        credential_id: credentialId,
        store_name: storeName,
        value,
      });
      navigate(`/credentials/${cred.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Add Credential</h1>
      </div>

      {error && <div className="error">{error}</div>}

      <form className="form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Credential ID</label>
          <input
            className="form-input"
            value={credentialId}
            onChange={(e) => setCredentialId(e.target.value)}
            required
            maxLength={255}
            placeholder="openai-api-key"
          />
          <span className="form-hint">
            A unique identifier for this credential
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">Store</label>
          <select
            className="form-select"
            value={storeName}
            onChange={(e) => setStoreName(e.target.value)}
          >
            <option value="postgres">postgres</option>
            <option value="bitwarden">bitwarden</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Value</label>
          <input
            className="form-input"
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
            placeholder="sk-..."
          />
          <span className="form-hint">
            The secret value (API key, token, etc.)
          </span>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Saving..." : "Add Credential"}
          </button>
          <Link to="/credentials" className="btn">
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
