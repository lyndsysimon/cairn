import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProviders, deleteProvider } from "../api/client";
import type { ModelProvider } from "../api/types";

export function ProviderListPage() {
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const data = await listProviders();
      setProviders(data.providers);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete provider "${name}"?`)) return;
    try {
      await deleteProvider(id);
      setProviders((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Model Providers</h1>
        <Link to="/providers/new" className="btn btn-primary">
          + New Provider
        </Link>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">Loading providers...</div>
      ) : providers.length === 0 ? (
        <div className="empty-state">
          <p>No model providers configured yet.</p>
          <Link to="/providers/new" className="btn btn-primary">
            Add your first provider
          </Link>
        </div>
      ) : (
        <table className="agent-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Models</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {providers.map((provider) => (
              <tr key={provider.id}>
                <td>
                  <Link
                    to={`/providers/${provider.id}`}
                    className="agent-name-link"
                  >
                    {provider.name}
                  </Link>
                </td>
                <td>
                  <code>{provider.provider_type}</code>
                </td>
                <td>
                  {provider.models.filter((m) => m.is_enabled).length} /{" "}
                  {provider.models.length}
                </td>
                <td>
                  <span
                    className={`status ${provider.is_enabled ? "status-active" : "status-inactive"}`}
                  >
                    {provider.is_enabled ? "enabled" : "disabled"}
                  </span>
                </td>
                <td>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() =>
                      handleDelete(provider.id, provider.name)
                    }
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
