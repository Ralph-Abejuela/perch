import { useEffect, useState } from "react";
import { api } from "./api";

interface SettingsInfo {
  plan: string;
  max_sites: number | null;
  max_agents: number | null;
  site_count: number;
  agent_count: number;
  open_conversations: number;
}

interface AgentRow {
  id: string;
  email: string;
  is_owner: boolean;
}

export default function Settings({ isOwner }: { isOwner: boolean }) {
  const [info, setInfo] = useState<SettingsInfo | null>(null);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    setInfo(await api<SettingsInfo>("/api/agent/settings"));
    setAgents(await api<AgentRow[]>("/api/agent/agents"));
  }
  useEffect(() => {
    load();
  }, []);

  async function changePlan(plan: string) {
    setError(null);
    setNotice(null);
    try {
      await api("/api/agent/settings/plan", { method: "POST", body: JSON.stringify({ plan }) });
      await load();
      setNotice(`Plan changed to ${plan}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function addAgent(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/agent/agents", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setEmail("");
      setPassword("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  if (!info) return <div className="pane muted">Loading…</div>;

  const limit = (max: number | null) => (max === null ? "unlimited" : max);

  return (
    <div className="pane">
      <h3>Plan</h3>
      <div className="card wide">
        <div className="row">
          <strong className="plan-name">{info.plan.toUpperCase()}</strong>
          {isOwner && info.plan === "free" && (
            <button onClick={() => changePlan("pro")}>Upgrade to Pro</button>
          )}
          {isOwner && info.plan === "pro" && (
            <button className="link" onClick={() => changePlan("free")}>Downgrade to Free</button>
          )}
        </div>
        <p className="muted">
          Sites: {info.site_count}/{limit(info.max_sites)} · Agents: {info.agent_count}/
          {limit(info.max_agents)} · Open conversations: {info.open_conversations}
        </p>
        {notice && <p className="notice">{notice}</p>}
      </div>

      <h3>Agents</h3>
      <ul className="list">
        {agents.map((a) => (
          <li key={a.id}>
            <div>
              <strong>{a.email}</strong>
              {a.is_owner && <span className="muted"> · owner</span>}
            </div>
          </li>
        ))}
      </ul>

      {isOwner && (
        <form onSubmit={addAgent} className="row">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="agent@email.com"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Temporary password"
            minLength={8}
            required
          />
          <button>Add agent</button>
        </form>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
