import { useEffect, useRef, useState } from "react";
import { ChevronRight, Pencil, Plus, SendHorizontal, Trash2 } from "lucide-react";
import { api, type Customer, type DraftGoal, type Suggestion } from "./api";
import type { PlanGoal } from "./FlightPlan";
import { PageBar } from "./Flows";
import { eur, month, TODAY } from "./format";

type Msg = { role: "user" | "assistant"; content: string };
type Row = DraftGoal & { _k?: number };   // _k: stable React key per row, never sent as a goal field the backend reads

const OPENING = "Tell me what you're working towards, soon and later. I'll check whether the amounts and dates are realistic for your budget.";
// Shown when the customer's own data suggests nothing yet; each one starts a turn with Autopilot.
const IDEAS = [
  ["Safety buffer", "I want a safety buffer for unexpected costs"],
  ["A trip", "I want to save for a trip"],
  ["Own home", "One day I'd like to buy my own home"],
] as const;
const MAX_GOALS = 5;

const addMonths = (iso: string, n: number) => {
  const d = new Date(iso + "T00:00:00");
  d.setMonth(d.getMonth() + n);
  return d.toISOString().slice(0, 10);
};
const horizonFor = (deadline: string): DraftGoal["horizon"] =>
  (new Date(deadline).getTime() - new Date(TODAY).getTime()) / 86_400_000 <= 183 ? "now" : "long";

/** Flight-plan view of a draft goal. ETA is recomputed here after the customer edits amount, pace or date. */
function toPlan(g: DraftGoal, pace: number): PlanGoal {
  const monthly = g.monthly_eur && g.monthly_eur > 0 ? g.monthly_eur : pace;
  const eta = monthly > 0 ? addMonths(TODAY, Math.ceil(g.target_eur / monthly)) : null;
  return { title: g.title || "Untitled", horizon: g.horizon, target: g.target_eur, saved: 0, deadline: g.deadline, eta,
           on_course: !!eta && eta <= g.deadline, reached: false };
}

const fromSuggestion = (s: Suggestion, priority: number): DraftGoal =>
  ({ title: s.title, type: s.type, horizon: s.horizon, target_eur: s.target_eur, deadline: s.deadline, priority, monthly_eur: 0 });

export function Onboarding({ c, onBack, onSaved, notify }: {
  c: Customer; onBack: () => void; onSaved: (c: Customer) => void; notify: (m: string) => void;
}) {
  const [history, setHistory] = useState<Msg[]>([{ role: "assistant", content: OPENING }]);
  const [draft, setDraft] = useState<Row[]>([]);
  const nextKey = useRef(1);
  // The engine's suggested pace per goal, from the last turn. Falls back to the customer's usual room split evenly.
  const [paces, setPaces] = useState<Record<string, number>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [turnsLeft, setTurnsLeft] = useState(6);
  const [picking, setPicking] = useState(false);       // choosing a new goal while some are already drafted
  const [editing, setEditing] = useState<number | null>(null);   // _k of the one goal whose fields are open
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" }); }, [history, busy]);

  const paceOf = (g: DraftGoal) => g.monthly_eur && g.monthly_eur > 0 ? g.monthly_eur : paces[g.title] ?? 0;
  const renumber = (d: DraftGoal[]) => d.map((g, i) => ({ ...g, priority: i + 1 }));
  const suggested = c.suggestions.filter((s) => !draft.some((g) => g.title.toLowerCase() === s.title.toLowerCase()));

  async function send(text: string) {
    const content = text.trim().slice(0, 500);
    if (!content || busy || turnsLeft <= 0) return;
    const next: Msg[] = [...history, { role: "user", content }];
    setHistory(next);
    setInput("");
    setBusy(true);
    try {
      const out = await api.onboarding(c.id, next, renumber(draft));
      setHistory([...next, { role: "assistant", content: out.reply }]);
      setDraft(out.goals.map((g) => ({ ...g, _k: nextKey.current++ })));
      setPaces(Object.fromEntries(out.goals.map((g) => [g.title, g.pace_eur ?? 0])));
      setTurnsLeft(out.turns_left);
      if (out.goals.length) setPicking(false);
    } catch (e) {
      setHistory([...next, { role: "assistant", content: `${(e as Error).message} You can still edit your goals above.` }]);
    } finally {
      setBusy(false);
    }
  }

  function edit(i: number, patch: Partial<DraftGoal>) {
    setDraft((d) => d.map((g, j) => (j !== i ? g : { ...g, ...patch, horizon: horizonFor(patch.deadline ?? g.deadline) })));
  }
  function add(g: DraftGoal, open = false) {
    const k = nextKey.current++;
    setDraft((d) => (d.length >= MAX_GOALS ? d : renumber([...d, { ...g, _k: k }])));
    setEditing(open ? k : null);
    setPicking(false);
  }
  const remove = (i: number) => setDraft((d) => renumber(d.filter((_, j) => j !== i)));

  async function confirm() {
    setBusy(true);
    try {
      onSaved(await api.saveGoals(c.id, renumber(draft)));
      notify("Goals saved. Autopilot now watches for what gets you there.");
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const valid = draft.length > 0 && draft.every((g) => g.title.trim() && g.target_eur > 0);
  const choosing = picking || draft.length === 0;
  const spoke = history.length > 1;

  const chat = (placeholder: string) => (
    <div className="spar">
      {spoke && (
        <div className="chat" ref={chatRef} aria-live="polite">
          {history.slice(1).map((m, i) => <div key={i} className={`bubble ${m.role}`}>{m.content}</div>)}
          {busy && <div className="bubble assistant" aria-label="Thinking"><span className="typing"><i /><i /><i /></span></div>}
        </div>
      )}
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <label htmlFor="say" className="sr-only">Your message</label>
        <input id="say" value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} autoComplete="off"
          placeholder={turnsLeft > 0 ? placeholder : "No questions left"} disabled={busy || turnsLeft <= 0} />
        <button className="btn" style={{ padding: "0 14px" }} aria-label="Send" disabled={busy || !input.trim() || turnsLeft <= 0}>
          <SendHorizontal size={20} />
        </button>
      </form>
    </div>
  );

  if (choosing) return (
    <>
      <PageBar title="Set your goals" onBack={draft.length ? () => setPicking(false) : onBack} />
      <div className="screen">
        <section aria-labelledby="pick">
          <h2 className="section-title" id="pick">What are you saving for?</h2>
          <div className="list">
            {suggested.map((s) => (
              <div className="row suggestion" key={s.key}>
                <div className="row-main wrap">
                  <div><strong>{s.title}</strong></div>
                  <div className="meta num">{eur(s.target_eur, true)} by {month(s.deadline)}</div>
                  <div className="small muted">{s.evidence.length ? s.evidence.join(" · ") : s.reason}</div>
                </div>
                <button className="btn secondary" type="button" disabled={busy} onClick={() => add(fromSuggestion(s, draft.length + 1))}>
                  <Plus size={16} /> Add
                </button>
              </div>
            ))}
            {suggested.length === 0 && IDEAS.map(([label, text]) => (
              <button key={label} className="row row-btn" type="button" disabled={busy} onClick={() => send(text)}>
                <div className="row-main" style={{ fontWeight: 600, color: "var(--navy)" }}>{label}</div>
                <ChevronRight size={18} aria-hidden="true" />
              </button>
            ))}
            <button className="row row-btn" type="button" disabled={busy}
              onClick={() => add({ title: "", type: "save_for", horizon: "long", target_eur: 1000, deadline: addMonths(TODAY, 12), priority: draft.length + 1, monthly_eur: 0 }, true)}>
              <Plus size={18} aria-hidden="true" /> Something else
            </button>
          </div>
        </section>
        <section aria-labelledby="tell">
          <h2 className="section-title" id="tell">Or tell Autopilot</h2>
          {chat("E.g. a trip to Japan next summer")}
        </section>
      </div>
    </>
  );

  return (
    <>
      <PageBar title="Your goals" onBack={onBack} />
      <div className="screen">
        <section aria-label="Your goals">
          <div className="list">
            {draft.map((g, i) => {
              const p = toPlan(g, paceOf(g));
              const k = g._k ?? -i;
              if (editing !== k) return (
                <button className="row row-btn" type="button" key={k} onClick={() => setEditing(k)} aria-label={`Edit ${g.title || "goal"}`}>
                  <div className="row-main wrap">
                    <div style={{ fontWeight: 600, color: "var(--navy)" }}>{g.title || "Untitled"}</div>
                    <div className="meta num">{eur(g.target_eur, true)} by {month(g.deadline)}
                      {paceOf(g) > 0 && <> · {eur(paceOf(g), true)} a month</>}</div>
                  </div>
                  {p.eta && <span className={`badge ${p.on_course ? "ok" : "off"}`}>{p.on_course ? "On track" : "Off track"}</span>}
                  <Pencil size={16} aria-hidden="true" />
                </button>
              );
              const enginePace = paces[g.title] ?? 0;
              return (
                <div className="goal-edit" key={k}>
                  <label className="field">Goal
                    <input type="text" value={g.title} maxLength={40} placeholder="E.g. Ski trip" autoFocus={!g.title}
                      onChange={(e) => edit(i, { title: e.target.value })} />
                  </label>
                  <div className="goal-edit-grid">
                    <label className="field">Target (€)
                      <input type="number" min={50} step={50} value={g.target_eur || ""}
                        onChange={(e) => edit(i, { target_eur: Math.max(0, Number(e.target.value)) })} />
                    </label>
                    <label className="field">Per month (€)
                      <input type="number" min={0} step={10} value={g.monthly_eur || ""} placeholder={enginePace > 0 ? String(Math.round(enginePace)) : ""}
                        onChange={(e) => edit(i, { monthly_eur: Math.max(0, Number(e.target.value)) })} />
                    </label>
                    <label className="field span-2">By when
                      <input type="date" min={addMonths(TODAY, 1)} value={g.deadline}
                        onChange={(e) => e.target.value && edit(i, { deadline: e.target.value })} />
                    </label>
                  </div>
                  <div className="small goal-edit-eta">
                    {p.eta
                      ? <span>Reached {month(p.eta)} · <span className={`badge ${p.on_course ? "ok" : "off"}`}>{p.on_course ? "On track" : "Off track"}</span></span>
                      : <span className="muted">Set a monthly amount to see when you get there</span>}
                  </div>
                  <div className="tip-actions">
                    <button className="btn secondary" type="button" disabled={!(g.title.trim() && g.target_eur > 0)} onClick={() => setEditing(null)}>Done</button>
                    <button className="btn-text quiet" type="button" onClick={() => remove(i)}><Trash2 size={16} /> Remove</button>
                  </div>
                </div>
              );
            })}
          </div>
          {draft.length < MAX_GOALS && (
            <button className="btn-text" type="button" style={{ paddingLeft: 0, marginTop: 8 }} disabled={busy} onClick={() => setPicking(true)}>
              <Plus size={16} aria-hidden="true" /> Add another goal
            </button>
          )}
        </section>
        <section aria-labelledby="spar">
          <h2 className="section-title" id="spar">Is this realistic?</h2>
          {chat("E.g. is € 300 a month enough?")}
        </section>
        <button className="btn block" style={{ marginTop: 24 }} disabled={busy || !valid} onClick={confirm}>Save goals</button>
      </div>
    </>
  );
}
