import { useState } from "react";
import { api, type Me } from "./api";

export default function Login({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const body =
        mode === "login" ? { email, password } : { tenant_name: tenantName, email, password };
      onSignedIn(await api<Me>(path, { method: "POST", body: JSON.stringify(body) }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <form className="card" onSubmit={submit}>
        <h2>{mode === "login" ? "Sign in" : "Create your workspace"}</h2>
        {mode === "signup" && (
          <input
            placeholder="Company / site name"
            value={tenantName}
            onChange={(e) => setTenantName(e.target.value)}
            required
          />
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password (min 8 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
        {error && <p className="error">{error}</p>}
        <button disabled={busy}>{busy ? "…" : mode === "login" ? "Sign in" : "Sign up"}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
          {mode === "login" ? "Need an account? Sign up" : "Have an account? Sign in"}
        </button>
      </form>
    </div>
  );
}
