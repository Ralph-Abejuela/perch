export interface Me {
  id: string;
  email: string;
  is_owner: boolean;
  tenant_id: string;
  tenant_name: string;
  tenant_plan: string;
}

export interface Site {
  id: string;
  name: string;
  key: string;
}

export interface ConvSummary {
  id: string;
  site_id: string;
  visitor_name: string | null;
  visitor_email: string | null;
  status: "open" | "closed";
  created_at: string;
  last_message: string | null;
}

export interface ChatMessage {
  id: string;
  sender: "visitor" | "agent";
  body: string;
  ts: string;
}

export interface Capture {
  id: string;
  site_id: string;
  email: string;
  body: string;
  resolved: boolean;
  ts: string;
}

export interface Page<T> {
  items: T[];
  has_more: boolean;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: init?.body ? { "content-type": "application/json" } : undefined,
    ...init,
  });
  if (res.status === 401) throw new Unauthorized();
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export class Unauthorized extends Error {}
