import { get, post, wsUrl } from "./api";

const SITE_KEY: string =
  (document.currentScript as HTMLScriptElement | null)?.getAttribute("data-site-key") ?? "";

const VISITOR_KEY = "perch:visitor_id";

function visitorId(): string {
  let id = localStorage.getItem(VISITOR_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(VISITOR_KEY, id);
  }
  return id;
}

interface ChatMessage {
  id: string;
  sender: "visitor" | "agent";
  body: string;
  ts: string;
}

let ws: WebSocket | null = null;
let conversationId: string | null = null;
const messages: ChatMessage[] = [];
let identifyInfo: { name?: string; email?: string } = {};

// --- WebSocket -----------------------------------------------------------

function connect(): void {
  if (ws || !conversationId) return;
  ws = new WebSocket(
    wsUrl(`/api/widget/${SITE_KEY}/ws?visitor_id=${visitorId()}&conversation_id=${conversationId}`),
  );
  ws.onopen = () => {
    if (Object.keys(identifyInfo).length) {
      ws!.send(JSON.stringify({ type: "identify", ...identifyInfo }));
    }
  };
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    if (event.type === "message" && !messages.some((m) => m.id === event.id)) {
      messages.push(event);
      render(messages);
    }
  };
  ws.onclose = () => {
    ws = null;
  };
}

// --- UI ------------------------------------------------------------------

const host = document.createElement("div");
const shadow = host.attachShadow({ mode: "open" });

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}

function render(msgs: ChatMessage[]): void {
  const body = msgs
    .map((m) => `<div class="msg ${m.sender}">${escapeHtml(m.body)}</div>`)
    .join("");
  shadow.innerHTML = `
    <style>
      :host { all: initial; }
      * { box-sizing: border-box; font-family: system-ui, sans-serif; }
      .panel {
        position: fixed; bottom: 84px; right: 24px; width: 320px; height: 420px;
        background: #fff; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.18);
        display: flex; flex-direction: column; overflow: hidden; z-index: 2147483000;
      }
      .head { background: #1a7f5a; color: #fff; padding: 12px 16px; font-weight: 600; }
      .log { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
      .msg { max-width: 80%; padding: 8px 12px; border-radius: 12px; font-size: 14px; line-height: 1.4; white-space: pre-wrap; }
      .msg.visitor { align-self: flex-end; background: #1a7f5a; color: #fff; }
      .msg.agent { align-self: flex-start; background: #eee; color: #111; }
      form { display: flex; border-top: 1px solid #e5e5e5; }
      input { flex: 1; border: 0; padding: 12px; font-size: 14px; outline: none; }
      button.send { border: 0; background: #1a7f5a; color: #fff; padding: 0 16px; font-weight: 600; cursor: pointer; }
      .bubble {
        position: fixed; bottom: 24px; right: 24px; width: 52px; height: 52px;
        border-radius: 50%; border: 0; background: #1a7f5a; color: #fff;
        font-size: 22px; cursor: pointer; z-index: 2147483001; box-shadow: 0 4px 14px rgba(0,0,0,.25);
      }
    </style>
    <div class="panel" part="panel">
      <div class="head">Chat with us</div>
      <div class="log" id="log">${body}</div>
      <form id="f">
        <input id="i" placeholder="Type a message…" />
        <button class="send">Send</button>
      </form>
    </div>
    <button class="bubble" id="bubble" aria-label="Toggle chat">💬</button>
  `;
  shadow.getElementById("bubble")!.addEventListener("click", toggle);
  shadow.getElementById("f")!.addEventListener("submit", onSend);
  const log = shadow.getElementById("log")!;
  log.scrollTop = log.scrollHeight;
}

function onSend(e: Event): void {
  e.preventDefault();
  const input = shadow.getElementById("i") as HTMLInputElement;
  const body = input.value.trim();
  if (!body || !conversationId) return;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "message", body }));
    input.value = "";
  } else {
    // REST fallback when the socket is not up.
    post<ChatMessage>(`/api/widget/${SITE_KEY}/conversations/${conversationId}/messages`, {
      visitor_id: visitorId(),
      body,
    }).then((msg) => {
      messages.push(msg);
      render(messages);
    });
  }
}

async function toggle(): Promise<void> {
  if (shadow.querySelector(".panel")) {
    shadow.querySelector(".panel")!.remove();
    return;
  }
  if (!conversationId) {
    const { conversation_id } = await post<{ conversation_id: string }>(
      `/api/widget/${SITE_KEY}/conversations`,
      { visitor_id: visitorId() },
    );
    conversationId = conversation_id;
    const history = await get<ChatMessage[]>(
      `/api/widget/${SITE_KEY}/conversations/${conversationId}/messages?visitor_id=${visitorId()}`,
    );
    messages.push(...history);
  }
  connect();
  render(messages);
}

// --- Public API ----------------------------------------------------------

export function identify(info: { name?: string; email?: string }): void {
  identifyInfo = { ...identifyInfo, ...info };
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "identify", ...identifyInfo }));
  }
}

export async function boot(): Promise<void> {
  await get(`/api/widget/${SITE_KEY}/config`); // fail fast on unknown key
  render(messages);
  document.body.appendChild(host);
}

boot();
