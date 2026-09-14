import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ChatMessage, type ConvSummary, type Page } from "./api";

function wsUrl(path: string): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}${path}`;
}

export default function Conversations() {
  const [convs, setConvs] = useState<ConvSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<"open" | "closed">("open");
  const [selected, setSelected] = useState<ConvSummary | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [draft, setDraft] = useState("");
  const [agentTyping, setAgentTyping] = useState(false); // visitor typing indicator
  const wsRef = useRef<WebSocket | null>(null);
  const pageRef = useRef(1);
  const logRef = useRef<HTMLDivElement | null>(null);

  const loadConvs = useCallback(async () => {
    const page = await api<Page<ConvSummary>>(
      `/api/agent/conversations?status=${statusFilter}`,
    );
    setConvs(page.items);
  }, [statusFilter]);

  const loadMessages = useCallback(async (convId: string, page: number) => {
    const res = await api<Page<ChatMessage>>(
      `/api/agent/conversations/${convId}/messages?page=${page}`,
    );
    pageRef.current = page;
    setHasMore(res.has_more);
    if (page === 1) setMessages(res.items);
    else setMessages((prev) => [...res.items, ...prev]);
  }, []);

  // Inbox list + refetch on filter change.
  useEffect(() => {
    loadConvs();
  }, [loadConvs]);

  // Agent WebSocket: realtime messages, typing, presence.
  useEffect(() => {
    const ws = new WebSocket(wsUrl("/api/agent/ws"));
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === "message") {
        if (selected && event.conversation_id === selected.id) {
          setMessages((prev) =>
            prev.some((m) => m.id === event.id) ? prev : [...prev, event],
          );
        }
        loadConvs();
      } else if (event.type === "typing" && selected && event.conversation_id === selected.id && event.sender === "visitor") {
        setAgentTyping(true);
        setTimeout(() => setAgentTyping(false), 3000);
      }
    };
    const heartbeat = setInterval(() => ws.readyState === 1 && ws.send(JSON.stringify({ type: "ping" })), 30000);
    return () => {
      clearInterval(heartbeat);
      ws.close();
      wsRef.current = null;
    };
  }, [selected?.id, loadConvs]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load history when selection changes.
  useEffect(() => {
    if (selected) loadMessages(selected.id, 1);
    else setMessages([]);
  }, [selected?.id, loadMessages]); // eslint-disable-line react-hooks/exhaustive-deps

  function scrollBottom() {
    requestAnimationFrame(() => {
      if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    });
  }

  function send(e: React.FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || !selected || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ type: "agent_message", conversation_id: selected.id, body }));
    setDraft("");
    scrollBottom();
  }

  function closeConv() {
    if (!selected || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ type: "close", conversation_id: selected.id }));
    setSelected({ ...selected, status: "closed" });
    loadConvs();
  }

  async function loadOlder() {
    if (selected) await loadMessages(selected.id, pageRef.current + 1);
  }

  return (
    <div className="split">
      <aside>
        <div className="toolbar">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as "open" | "closed")}>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <ul className="inbox">
          {convs.map((c) => (
            <li
              key={c.id}
              className={selected?.id === c.id ? "active" : ""}
              onClick={() => setSelected(c)}
            >
              <div className="row">
                <strong>{c.visitor_name ?? `Visitor ${c.id.slice(0, 6)}`}</strong>
                <span className="muted">{new Date(c.created_at).toLocaleDateString()}</span>
              </div>
              <div className="muted ellipsis">{c.last_message ?? "No messages yet"}</div>
            </li>
          ))}
          {convs.length === 0 && <li className="muted">No {statusFilter} conversations.</li>}
        </ul>
      </aside>

      {selected ? (
        <section className="chat">
          <div className="toolbar">
            <span>
              {selected.visitor_name ?? `Visitor ${selected.id.slice(0, 6)}`}
              {selected.visitor_email ? ` · ${selected.visitor_email}` : ""}
            </span>
            <span className="spacer" />
            <span className={`badge ${selected.status}`}>{selected.status}</span>
            {selected.status === "open" && <button onClick={closeConv}>Close</button>}
          </div>
          <div className="log" ref={logRef}>
            {hasMore && <button className="link" onClick={loadOlder}>Load older</button>}
            {messages.map((m) => (
              <div key={m.id} className={`msg ${m.sender}`}>
                {m.body}
              </div>
            ))}
            {agentTyping && <div className="muted typing">visitor is typing…</div>}
          </div>
          {selected.status === "open" ? (
            <form onSubmit={send}>
              <input
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  wsRef.current?.send(JSON.stringify({ type: "typing", conversation_id: selected.id }));
                }}
                placeholder="Reply…"
              />
              <button>Send</button>
            </form>
          ) : (
            <p className="muted">This conversation is closed.</p>
          )}
        </section>
      ) : (
        <section className="center muted">Select a conversation</section>
      )}
    </div>
  );
}
