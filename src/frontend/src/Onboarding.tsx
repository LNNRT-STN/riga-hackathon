import { useEffect, useRef, useState } from "react";
import { Plane, SendHorizontal, Trash2 } from "lucide-react";
import { api, type Customer, type DraftGoal } from "./api";
import { Route, type PlanGoal } from "./FlightPlan";
import { PageBar } from "./Flows";
import { eur, TODAY } from "./format";

type Msg = { role: "user" | "assistant"; content: string };

const OPENING = "Where do you want to fly to? Tell me what you're working towards, soon and later. A trip this winter, a safety buffer, your own home one day?";
const DESTINATIONS = [
  ["Own home", "One day I'd like to buy my own home"],
  ["Travel", "I want to save for a trip"],
  ["Safety buffer", "I want a safety buffer for unexpected costs"],
  ["Studies", "I want to save for studies"],
  ["Own business", "I'd like to start my own business"],
  ["Family", "I want to support my family"],
] as const;

const addMonths = (iso: string, n: number) => {
  const d = new Date(iso + "T00:00:00");
  d.setMonth(d.getMonth() + n);
  return d.toISOString().slice(0, 10);
};

/** Flight-plan view of a draft goal. The ETA is recomputed here after the customer edits amount or date. */
function toPlan(g: DraftGoal): PlanGoal {
  const monthly = g.monthly_eur ?? 0;
  const eta = monthly > 0 ? addMonths(TODAY, Math.ceil(g.target_eur / monthly)) : null;
  return { title: g.title, horizon: g.horizon, target: g.target_eur, saved: 0, deadline: g.deadline, eta,
           on_course: !!eta && eta <= g.deadline, reached: false };
}

export function Onboarding({ c, onBack, onSaved, notify }: {
  c: Customer; onBack: () => void; onSaved: (c: Customer) => void; notify: (m: string) => void;
}) {
  const [history, setHistory] = useState<Msg[]>([{ role: "assistant", content: OPENING }]);
  const [draft, setDraft] = useState<DraftGoal[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [turnsLeft, setTurnsLeft] = useState(6);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" }); }, [history, busy]);

  async function send(text: string) {
    const content = text.trim().slice(0, 500);
    if (!content || busy || turnsLeft <= 0) return;
    const next: Msg[] = [...history, { role: "user", content }];
    setHistory(next);
    setInput("");
    setBusy(true);
    try {
      const out = await api.onboarding(c.id, next);
      setHistory([...next, { role: "assistant", content: out.reply }]);
      setDraft(out.goals);
      setTurnsLeft(out.turns_left);
    } catch (e) {
      setHistory([...next, { role: "assistant", content: `${(e as Error).message} You can still pick destinations below.` }]);
    } finally {
      setBusy(false);
    }
  }

  function edit(i: number, patch: Partial<DraftGoal>) {
    setDraft((d) => d.map((g, j) => {
      if (j !== i) return g;
      const n = { ...g, ...patch };
      const days = (new Date(n.deadline).getTime() - new Date(TODAY).getTime()) / 86_400_000;
      return { ...n, horizon: days <= 183 ? "now" : "long" };
    }));
  }

  async function confirm() {
    setBusy(true);
    try {
      onSaved(await api.saveGoals(c.id, draft.map((g, i) => ({ ...g, priority: i + 1 }))));
      notify("Flight plan confirmed. Autopilot now watches for what gets you there.");
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageBar title="Plan your route" onBack={onBack} />
      <div className="chat" ref={chatRef} aria-live="polite">
        {history.map((m, i) => <div key={i} className={`bubble ${m.role}`}>{m.content}</div>)}
        {busy && <div className="bubble assistant" aria-label="Thinking"><span className="typing"><i /><i /><i /></span></div>}
        {draft.length === 0 && !busy && (
          <div className="chips" style={{ flexWrap: "wrap" }}>
            {DESTINATIONS.map(([label, text]) => (
              <button key={label} className="chip" onClick={() => send(text)}><Plane size={14} /> {label}</button>
            ))}
          </div>
        )}
      </div>
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <label htmlFor="say" className="sr-only">Your answer</label>
        <input id="say" value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} autoComplete="off"
          placeholder={turnsLeft > 0 ? "E.g. skiing in February, a flat in a few years" : "Confirm your plan below"}
          disabled={busy || turnsLeft <= 0} />
        <button className="btn" style={{ padding: "0 14px" }} aria-label="Send" disabled={busy || !input.trim() || turnsLeft <= 0}>
          <SendHorizontal size={20} />
        </button>
      </form>
      <div className="plan-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <strong style={{ color: "var(--navy)" }}>Your flight plan</strong>
          <span className="meta">Nothing is saved until you confirm</span>
        </div>
        {draft.length ? (
          <>
            <Route goals={draft.map(toPlan)} />
            {draft.map((g, i) => {
              const p = toPlan(g);
              return (
                <div key={i} style={{ display: "grid", gap: 6, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: "var(--navy)" }}>{g.title} <span className="meta">· {g.horizon === "now" ? "Stopover" : "Destination"}</span></strong>
                    <button className="icon-btn" style={{ width: 36, height: 36 }} aria-label={`Remove ${g.title}`}
                      onClick={() => setDraft((d) => d.filter((_, j) => j !== i))}><Trash2 size={16} /></button>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <label className="field">Target (€)
                      <input type="number" min={50} step={50} value={g.target_eur}
                        onChange={(e) => edit(i, { target_eur: Math.max(1, Number(e.target.value)) })} />
                    </label>
                    <label className="field">Arrive by
                      <input type="date" min={addMonths(TODAY, 1)} value={g.deadline}
                        onChange={(e) => e.target.value && edit(i, { deadline: e.target.value })} />
                    </label>
                  </div>
                  <span className="small">
                    {p.eta ? <>At about {eur(g.monthly_eur ?? 0, true)} a month: arrives {new Date(p.eta).toLocaleDateString("en-GB", { month: "short", year: "numeric" })} · </> : "No room in the budget yet · "}
                    <span className={`badge ${p.on_course ? "ok" : "off"}`}>{p.on_course ? "On course" : "Off course"}</span>
                  </span>
                </div>
              );
            })}
          </>
        ) : (
          <p className="small muted">Your destinations and stopovers appear here as you talk.</p>
        )}
        <button className="btn block" disabled={busy || draft.length === 0} onClick={confirm}>Confirm flight plan</button>
      </div>
    </>
  );
}
