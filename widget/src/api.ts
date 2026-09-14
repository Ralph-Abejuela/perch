const API_BASE: string =
  (document.currentScript as HTMLScriptElement | null)?.getAttribute("data-api") ?? "";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function wsUrl(path: string): string {
  const base = new URL(API_BASE || window.location.origin);
  const proto = base.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${base.host}${path}`;
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}
