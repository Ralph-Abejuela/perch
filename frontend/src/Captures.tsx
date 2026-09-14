import { useEffect, useState } from "react";
import { api, type Capture } from "./api";

export default function Captures() {
  const [captures, setCaptures] = useState<Capture[]>([]);

  async function load() {
    setCaptures(await api<Capture[]>("/api/agent/captures"));
  }
  useEffect(() => {
    load();
  }, []);

  async function resolve(id: string, resolved: boolean) {
    await api(`/api/agent/captures/${id}/resolve`, { method: "POST", body: JSON.stringify({ resolved }) });
    await load();
  }

  return (
    <div className="pane">
      <h3>Offline captures</h3>
      <ul className="list">
        {captures.map((c) => (
          <li key={c.id}>
            <div>
              <strong>{c.email}</strong> <span className="muted">{new Date(c.ts).toLocaleString()}</span>
              <div>{c.body}</div>
            </div>
            <button onClick={() => resolve(c.id, !c.resolved)}>
              {c.resolved ? "Reopen" : "Resolve"}
            </button>
          </li>
        ))}
        {captures.length === 0 && <li className="muted">Nothing here.</li>}
      </ul>
    </div>
  );
}
