import { useEffect, useState } from "react";
import { api, Unauthorized, type Me } from "./api";
import Login from "./Login";
import Conversations from "./Conversations";
import Sites from "./Sites";
import Captures from "./Captures";

type Tab = "conversations" | "sites" | "captures";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("conversations");

  useEffect(() => {
    api<Me>("/api/auth/me")
      .then(setMe)
      .catch((e) => {
        if (!(e instanceof Unauthorized)) console.error(e);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="center">Loading…</div>;
  if (!me) return <Login onSignedIn={setMe} />;

  return (
    <div className="shell">
      <header>
        <strong>Perch</strong>
        <span className="muted">{me.tenant_name} · {me.tenant_plan}</span>
        <nav>
          {(["conversations", "sites", "captures"] as Tab[]).map((t) => (
            <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
        <button
          className="link"
          onClick={async () => {
            await api("/api/auth/logout", { method: "POST" });
            setMe(null);
          }}
        >
          Sign out
        </button>
      </header>
      <main>
        {tab === "conversations" && <Conversations />}
        {tab === "sites" && <Sites />}
        {tab === "captures" && <Captures />}
      </main>
    </div>
  );
}
