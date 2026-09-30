export type Option = {
  id: string;
  type: "transfer" | "form" | "info" | "handoff";
  kbc: boolean;
  label: string;
  detail: string;
  amount?: number;
  from?: string;
  to?: string;
  advisor?: string;
  fields?: Record<string, string>;
  always?: { keep: number; cap: number };
};

export type Card = {
  situation_id: string;
  instance_key: string;
  kind: "help" | "product";
  risk: "critical" | "normal" | "regulated";
  action: "transfer" | "form" | "options" | "handoff" | "info";
  title: string;
  body: string;
  benefit: string;
  primary: string;
  includes_kbc_product: boolean;
  goal: { id: number; title: string; saved: number; target: number } | null;
  options: Option[];
  why: { evidence: string[]; confidence: string; checked_by: string; customer_eur: number; score: number };
};

export type Goal = {
  id?: number;
  title: string;
  horizon: "now" | "long";
  type: string;
  target: number;
  saved: number;
  deadline: string;
  eta: string | null;
  on_course: boolean;
  reached: boolean;
  monthly: number;
};

export type Customer = {
  id: number;
  name: string;
  persona: string;
  onboarded: boolean;
  balance: number;
  savings: number;
  mode: "quiet" | "normal" | "proactive";
  consent_help: boolean;
  consent_product: boolean;
  value_created: number;
  transactions: { day: string; amount: number; counterparty: string }[];
  card: Card | null;
  considered: { name: string; status: string; status_text: string; score: number | null; customer_eur: number; kind: string }[];
  bar: number;
  goals: Goal[];
  rules: { id: number; goal: string; keep: number; cap: number; next_run: string; preview: number }[];
  memory: string[];
  log: { day: string; text: string }[];
};

export type Result = { type: string; lines: string[]; advisor?: string | null };

export type DraftGoal = {
  title: string;
  type: string;
  horizon: "now" | "long";
  target_eur: number;
  deadline: string;
  priority: number;
  monthly_eur?: number;
  eta?: string | null;
  on_course?: boolean;
};

export type Funnel = {
  customers: number; with_candidate: number; confirmed: number; shown: number; help: number; product: number;
  customer_eur: number; kbc_eur: number; trust: number; holdout: number; holdout_shown: number; scale: number;
  cost_per_day_usd: number; jev_per_day_usd: number; ai_mode: string;
  situations: { id: string; name: string; audience: string; kind: string; detected: number; shown: number }[];
};

export type Engine = {
  funnel: Funnel;
  catalogue: { id: string; name: string; audience: string; kind: string; risk: string; action: string; check: string; question: string }[];
  custom: { text: string; sample: number; matches: number; source: string }[];
};

export type Screened = {
  text: string; sample: number; matches: number; estimate: number; source: string;
  examples: { customer: string; confidence: number; evidence: string[] }[];
};

export type OnboardingTurn = { reply: string; goals: DraftGoal[]; turns_left: number; source: "live" | "offline" };

async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, body === undefined ? undefined : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? "Something went wrong. Please try again.");
  return data as T;
}

export const api = {
  customers: () => call<{ id: number; name: string; persona: string }[]>("/customers"),
  customer: (id: number) => call<Customer>(`/customers/${id}`),
  respond: (id: number, body: { instance_key: string; response: string; option_id?: string; always?: boolean }) =>
    call<{ result: Result; view: Customer }>(`/customers/${id}/respond`, body),
  settings: (id: number, body: Partial<Pick<Customer, "mode" | "consent_help" | "consent_product">>) =>
    call<Customer>(`/customers/${id}/settings`, body),
  resetMemory: (id: number) => call<Customer>(`/customers/${id}/reset-memory`, {}),
  revokeRule: (id: number, rule: number) => call<Customer>(`/customers/${id}/revoke-rule/${rule}`, {}),
  onboarding: (id: number, history: { role: "user" | "assistant"; content: string }[]) =>
    call<OnboardingTurn>(`/customers/${id}/onboarding`, { history }),
  saveGoals: (id: number, goals: DraftGoal[]) => call<Customer>(`/customers/${id}/goals`, { goals }),
  engine: () => call<Engine>("/engine"),
  addSituation: (text: string) => call<Screened>("/situations", { text }),
  resetDemo: () => call<{ ok: boolean }>("/reset-demo", {}),
};
