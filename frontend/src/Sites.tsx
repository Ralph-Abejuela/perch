import { useEffect, useState } from "react";
import { api, type Site } from "./api";

export default function Sites() {
  const [sites, setSites] = useState<Site[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setSites(await api<Site[]>("/api/sites"));
  }
  useEffect(() => {
    load();
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/sites", { method: "POST", body: JSON.stringify({ name }) });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function remove(id: string) {
    await api(`/api/sites/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="pane">
      <h3>Your sites</h3>
      <form onSubmit={create} className="row">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New site name" required />
        <button>Add site</button>
      </form>
      {error && <p className="error">{error}</p>}
      <ul className="list">
        {sites.map((s) => (
          <li key={s.id}>
            <div>
              <strong>{s.name}</strong>
              <div className="muted mono">key: {s.key}</div>
              <code className="snippet">
                {`<script src="https://YOUR-API-DOMAIN/widget.js" data-site-key="${s.key}" data-api="https://YOUR-API-DOMAIN"></script>`}
              </code>
            </div>
            <button className="danger" onClick={() => remove(s.id)}>Delete</button>
          </li>
        ))}
        {sites.length === 0 && <li className="muted">No sites yet.</li>}
      </ul>
    </div>
  );
}
