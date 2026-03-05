import { useState, useEffect, useRef } from "react";
import { listCredentials, createCredential } from "../api/client";
import type { Credential } from "../api/types";

interface CredentialSelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function CredentialSelect({ value, onChange }: CredentialSelectProps) {
  const [query, setQuery] = useState("");
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [open, setOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  // Modal form state
  const [newCredentialId, setNewCredentialId] = useState("");
  const [newStoreName, setNewStoreName] = useState("postgres");
  const [newValue, setNewValue] = useState("");
  const [creating, setCreating] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && !loaded) {
      listCredentials()
        .then((res) => {
          setCredentials(res.credentials);
          setLoaded(true);
        })
        .catch(() => setLoaded(true));
    }
  }, [open, loaded]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = credentials.filter((c) =>
    c.credential_id.toLowerCase().includes(query.toLowerCase()),
  );

  function handleSelect(credentialId: string) {
    onChange(credentialId);
    setQuery("");
    setOpen(false);
  }

  function handleFocus() {
    setOpen(true);
    setQuery("");
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value);
    onChange(e.target.value);
    if (!open) setOpen(true);
  }

  function openModal() {
    setModalOpen(true);
    setOpen(false);
    setNewCredentialId("");
    setNewStoreName("postgres");
    setNewValue("");
    setModalError(null);
  }

  async function handleCreateCredential() {
    if (!newCredentialId.trim() || !newValue.trim()) return;
    setCreating(true);
    setModalError(null);
    try {
      const created = await createCredential({
        credential_id: newCredentialId.trim(),
        store_name: newStoreName,
        value: newValue,
      });
      setCredentials((prev) => [...prev, created]);
      onChange(created.credential_id);
      setQuery("");
      setModalOpen(false);
    } catch (e) {
      setModalError(String(e));
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <div className="credential-select" ref={containerRef}>
        <input
          ref={inputRef}
          className="form-input"
          style={{ width: "100%" }}
          value={open ? query || value : value}
          onChange={handleInputChange}
          onFocus={handleFocus}
          placeholder="Select or type a credential ID"
        />
        {open && (
          <ul className="credential-dropdown">
            {filtered.map((c) => (
              <li
                key={c.id}
                className="credential-dropdown-item"
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(c.credential_id);
                }}
              >
                <div>{c.credential_id}</div>
                <div className="credential-dropdown-item-secondary">
                  {c.store_name}
                </div>
              </li>
            ))}
            {filtered.length === 0 && loaded && (
              <li className="credential-dropdown-item" style={{ color: "var(--color-text-secondary)" }}>
                No matching credentials
              </li>
            )}
            <li
              className="credential-dropdown-item credential-dropdown-create"
              onMouseDown={(e) => {
                e.preventDefault();
                openModal();
              }}
            >
              + Create new credential...
            </li>
          </ul>
        )}
      </div>

      {modalOpen && (
        <div className="modal-overlay" onMouseDown={() => setModalOpen(false)}>
          <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
            <h2>New Credential</h2>
            {modalError && (
              <div className="error" style={{ marginBottom: "1rem" }}>
                {modalError}
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div className="form-group">
                <label className="form-label">Credential ID</label>
                <input
                  className="form-input"
                  value={newCredentialId}
                  onChange={(e) => setNewCredentialId(e.target.value)}
                  placeholder="anthropic-api-key"
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label className="form-label">Store</label>
                <select
                  className="form-select"
                  value={newStoreName}
                  onChange={(e) => setNewStoreName(e.target.value)}
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
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="Secret value"
                />
              </div>
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCreateCredential}
                  disabled={creating || !newCredentialId.trim() || !newValue.trim()}
                >
                  {creating ? "Creating..." : "Create"}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setModalOpen(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
