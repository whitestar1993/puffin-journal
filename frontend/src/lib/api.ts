// Thin client for the JSON API. All requests are same-origin; the X-Puffin
// header is the backend's CSRF guard for state-changing calls.

export type Tag = { id: number; name: string; archived: boolean; usage: number };
export type Prompt = { id: number; text: string; quick_answers: string[]; active: boolean };
export type Entry = {
  date: string;
  mood: number;
  energy: number | null;
  sleep: number | null;
  tags: { id: number; name: string }[];
  prompt_id: number | null;
  prompt_text: string | null;
  prompt_answer: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
};
export type EntryIn = {
  mood: number;
  energy: number | null;
  sleep: number | null;
  tag_ids: number[];
  prompt_id: number | null;
  prompt_answer: string | null;
  note: string | null;
};
export type Day = { date: string; today: string; entry: Entry | null; prompt: Prompt | null };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const authEvents = new EventTarget();

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      "X-Puffin": "1",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && path !== "/auth/login") authEvents.dispatchEvent(new Event("logout"));
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const data = await res.json();
      msg = typeof data.detail === "string" ? data.detail : "Please check your input";
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const qs = (params: Record<string, string | number | (string | number)[] | undefined | null>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    for (const item of Array.isArray(v) ? v : [v]) p.append(k, String(item));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  me: () => request<{ username: string }>("GET", "/auth/me"),
  login: (username: string, password: string) =>
    request<{ username: string }>("POST", "/auth/login", { username, password }),
  logout: () => request<void>("POST", "/auth/logout"),

  today: () => request<{ today: string; tz: string }>("GET", "/today"),
  day: (date: string) => request<Day>("GET", `/days/${date}`),
  saveEntry: (date: string, body: EntryIn) => request<Entry>("PUT", `/entries/${date}`, body),
  deleteEntry: (date: string) => request<void>("DELETE", `/entries/${date}`),
  entries: (opts: { q?: string; tag?: number[]; before?: string; limit?: number }) =>
    request<Entry[]>("GET", `/entries${qs(opts)}`),

  tags: (includeArchived = false) =>
    request<Tag[]>("GET", `/tags${qs({ include_archived: includeArchived ? "true" : undefined })}`),
  createTag: (name: string) => request<Tag>("POST", "/tags", { name }),
  updateTag: (id: number, patch: { name?: string; archived?: boolean }) =>
    request<Tag>("PATCH", `/tags/${id}`, patch),
  deleteTag: (id: number) => request<{ result: string }>("DELETE", `/tags/${id}`),

  prompts: () => request<Prompt[]>("GET", "/prompts"),
  createPrompt: (text: string, quick_answers: string[]) =>
    request<Prompt>("POST", "/prompts", { text, quick_answers }),
  updatePrompt: (id: number, patch: Partial<Omit<Prompt, "id">>) =>
    request<Prompt>("PATCH", `/prompts/${id}`, patch),
  deletePrompt: (id: number) => request<void>("DELETE", `/prompts/${id}`),
};
