import { useEffect, useRef } from "react";
import { ArrowLeft, ArrowRight, RotateCcw, Target, UserRoundPlus } from "lucide-react";
import type { Customer, Notification } from "./api";
import { eur, month } from "./format";

export type Person = { id: number; name: string; persona: string };
type Where = "start" | "autopilot" | "onboarding";

export type TourStep = {
  title: string;
  body: string;
  who?: number | "try";   // which customer the phone shows; "try" is the visitor's own
  view?: Where;
  engine?: boolean;
  note?: Notification;    // push notification shown on the phone for this beat
  evidence?: string[];    // lower-case counterparty keywords: what Autopilot saw, listed beside the phone
};

const BAS = 6, JURRE = 7;

// The jury pipeline: the deck's ring story first, then their own goal, actions, scale, and the other customers.
export const STEPS: TourStep[] = [
  { who: BAS, view: "start", evidence: ["bloemen"],
    title: "Bas is saving for a ring",
    body: "Bas buys flowers regularly. He set one goal in Autopilot." },
  { who: JURRE, view: "start", evidence: ["payconiq", "bloemen"],
    title: "His friend Jurre buys flowers now",
    body: "Jurre splits bills with Bas on Payconiq. This month he bought flowers twice. He has no goals yet." },
  { who: JURRE, view: "start",
    note: { title: "Saving for something special?", body: "Autopilot has a goal suggestion based on your payments. Nothing is set up until you say so." },
    title: "Autopilot suggests a ring to Jurre",
    body: "Tap the notification on Jurre's phone. He sees “1 person in your Payconiq circle”, never Bas's name. Add the goal and save it." },
  { who: "try", view: "onboarding",
    title: "Now set your own goal",
    body: "You're a new customer with an ordinary month. Pick a goal and ask Autopilot if it's realistic." },
  { who: "try", view: "autopilot",
    title: "Fast-forward your month",
    body: "On the Autopilot tab, pick a moment. Autopilot only speaks up when that beats doing nothing, and you approve every money movement." },
  { engine: true,
    title: "One engine for 2.000 customers",
    body: "The same rules run for every customer, no segments. Type a new situation to screen it live: one catalogue row, for 2.000 customers or 2,3 million." },
  { title: "More customers, same engine",
    body: "Each customer gets at most one card, or none. Pick one to load them in the phone." },
];

export function Tour({ step, c, people, tryId, busy, onGo, onTry, onRestart, onPick }: {
  step: number; c: Customer | null; people: Person[]; tryId: number | null; busy: boolean;
  onGo: (i: number) => void; onTry: () => void; onRestart: () => void; onPick: (id: number) => void;
}) {
  const s = STEPS[step];
  const heading = useRef<HTMLHeadingElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }   // don't steal focus on page load
    heading.current?.focus({ preventScroll: true });
  }, [step]);

  const here = c && (s.who === "try" ? c.is_try : c.id === s.who) ? c : null;
  // One line per counterparty: what Autopilot saw, not the whole statement.
  const seen = new Map<string, { n: number; sum: number }>();
  for (const t of here && s.evidence ? here.transactions : []) {
    if (!s.evidence!.some((w) => t.counterparty.toLowerCase().includes(w))) continue;
    const x = seen.get(t.counterparty) ?? { n: 0, sum: 0 };
    seen.set(t.counterparty, { n: x.n + 1, sum: x.sum + Math.abs(t.amount) });
  }
  const ringDone = s.note && here && !here.suggestions.some((x) => x.key === "wedding");
  const needsTry = s.who === "try" && !tryId;

  return (
    <aside className="tour panel" aria-labelledby="tour-title">
      <nav aria-label="Demo steps">
        <ol className="tour-steps">
          {STEPS.map((x, i) => (
            <li key={x.title}>
              <button type="button" aria-label={`Step ${i + 1}: ${x.title}`} aria-current={i === step ? "step" : undefined}
                data-done={i < step || undefined} onClick={() => onGo(i)} />
            </li>
          ))}
        </ol>
      </nav>

      <div className="tour-body" aria-live="polite">
        <h2 id="tour-title" className="section-title" ref={heading} tabIndex={-1}>{s.title}</h2>
        <p className="small">{s.body}</p>

        {here && s.who === BAS && here.goals.map((g) => (
          <p key={g.title} className="small tour-goal"><Target size={16} aria-hidden="true" />
            <span><strong>{g.title}</strong> · <span className="num">{eur(g.saved, true)} of {eur(g.target, true)} by {month(g.deadline)}</span></span></p>
        ))}
        {seen.size > 0 && (
          <div>
            <h3 className="tour-sub">What Autopilot saw</h3>
            <div className="list">
              {[...seen].map(([who, x]) => (
                <div className="row tour-seen" key={who}>
                  <div className="row-main"><div>{who}</div><div className="meta">{x.n} {x.n === 1 ? "payment" : "payments"}</div></div>
                  <span className="row-amount num">{eur(x.sum)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {ringDone && (
          <div className="msg info small">Jurre already has this goal.
            <button className="btn-text" onClick={onRestart} disabled={busy}><RotateCcw size={16} /> Restart the tour</button></div>
        )}

        {s.view === "autopilot" && here && !here.onboarded && (
          <p className="msg info small">Save a goal under “Your turn” first; the moments appear after that.</p>
        )}
        {needsTry && (
          <button className="btn block" onClick={onTry} disabled={busy}><UserRoundPlus size={18} /> Start as a new customer</button>
        )}

        {!s.who && !s.engine && (
          <div className="list">
            {[...people].sort((a, b) => Number([BAS, JURRE].includes(a.id)) - Number([BAS, JURRE].includes(b.id))).map((p) => (
              <button key={p.id} type="button" className="row row-btn" aria-current={c?.id === p.id ? "true" : undefined}
                onClick={() => onPick(p.id)} disabled={busy}>
                <div className="row-main wrap">
                  <div style={{ fontWeight: 600, color: "var(--navy)" }}>{p.name}</div>
                  <div className="meta">{p.persona}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="tour-nav">
        <button className="btn secondary" onClick={() => onGo(step - 1)} disabled={step === 0} aria-label="Back"><ArrowLeft size={18} /></button>
        <span className="meta num">{step + 1} / {STEPS.length}</span>
        {step < STEPS.length - 1
          ? <button className="btn" onClick={() => onGo(step + 1)}>Next <ArrowRight size={18} /></button>
          : <button className="btn secondary" onClick={onRestart} disabled={busy}><RotateCcw size={18} /> Restart</button>}
      </div>
    </aside>
  );
}
