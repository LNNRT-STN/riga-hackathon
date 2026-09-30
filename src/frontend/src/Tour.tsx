import { useEffect, useRef } from "react";
import { ArrowLeft, ArrowRight, RotateCcw, Target, UserRoundPlus } from "lucide-react";
import type { Customer, Notification } from "./api";
import { day, eur, month } from "./format";

export type Person = { id: number; name: string; persona: string };
type Where = "start" | "autopilot" | "onboarding";

export type TourStep = {
  chapter: string;
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
  { chapter: "The ring story", who: BAS, view: "start", evidence: ["bloemen"],
    title: "Bas is saving for a ring",
    body: "Bas has bought flowers regularly for months. Then he set a goal in Autopilot: a wedding ring, € 3.000 by September 2027." },
  { chapter: "The ring story", who: JURRE, view: "start", evidence: ["payconiq", "bloemen"],
    title: "His friend Jurre buys flowers now",
    body: "Jurre and Bas split drinks and pizza through Payconiq. This month Jurre bought flowers twice. He has no goals yet." },
  { chapter: "The ring story", who: JURRE, view: "start",
    note: { title: "Saving for something special?", body: "Autopilot has a goal suggestion based on your payments. Nothing is set up until you say so." },
    title: "Autopilot suggests a ring goal to Jurre",
    body: "Same pattern as Bas: flowers, and a friend in his Payconiq circle saving for a ring. Tap the notification on Jurre's phone. " +
      "He sees “1 person in your Payconiq circle”, never Bas's name. Add the goal and save it." },
  { chapter: "Your turn", who: "try", view: "onboarding",
    title: "Now set your own goal",
    body: "You get a fresh customer with an ordinary month of payments. Pick a suggestion or tell Autopilot what you're working " +
      "towards; it checks whether the amounts and dates are realistic." },
  { chapter: "Watch it act", who: "try", view: "autopilot",
    title: "Fast-forward your month",
    body: "On your Autopilot tab, pick a moment under “What happens next?”. Autopilot sends a notification only when helping beats " +
      "doing nothing, and every money movement waits for your approval on a review screen." },
  { chapter: "At scale", engine: true,
    title: "One engine for 2.000 customers",
    body: "The same rules run over every synthetic customer: no segments, no hand-made journeys. Type a new situation to see it " +
      "screened live. A new situation is one row in the catalogue, whether for 2.000 customers or 2,3 million." },
  { chapter: "More customers",
    title: "More customers, same engine",
    body: "Each customer gets at most one card, or none when doing nothing is better. Pick one to load them in the phone." },
];
const CHAPTERS = [...new Set(STEPS.map((s) => s.chapter))];

export function Tour({ step, c, people, tryId, busy, onGo, onTry, onRestart, onPick }: {
  step: number; c: Customer | null; people: Person[]; tryId: number | null; busy: boolean;
  onGo: (i: number) => void; onTry: () => void; onRestart: () => void; onPick: (id: number) => void;
}) {
  const s = STEPS[step];
  const beats = STEPS.filter((x) => x.chapter === s.chapter);
  const beat = beats.indexOf(s);
  const heading = useRef<HTMLHeadingElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }   // don't steal focus on page load
    heading.current?.focus({ preventScroll: true });
  }, [step]);

  const here = c && (s.who === "try" ? c.is_try : c.id === s.who) ? c : null;
  const seen = here && s.evidence
    ? here.transactions.filter((t) => s.evidence!.some((w) => t.counterparty.toLowerCase().includes(w))) : [];
  const ringDone = s.note && here && !here.suggestions.some((x) => x.key === "wedding");
  const needsTry = s.who === "try" && !tryId;

  return (
    <aside className="tour panel" aria-labelledby="tour-title">
      <nav aria-label="Demo chapters">
        <ol className="tour-chapters">
          {CHAPTERS.map((ch) => (
            <li key={ch}>
              <button type="button" aria-current={ch === s.chapter ? "step" : undefined}
                onClick={() => onGo(STEPS.findIndex((x) => x.chapter === ch))}>{ch}</button>
            </li>
          ))}
        </ol>
      </nav>

      <div className="tour-body" aria-live="polite">
        <h2 id="tour-title" className="section-title" ref={heading} tabIndex={-1}>{s.title}</h2>
        {beats.length > 1 && <p className="meta">Step {beat + 1} of {beats.length}</p>}
        <p className="small">{s.body}</p>

        {here && s.who === BAS && here.goals.map((g) => (
          <p key={g.title} className="small tour-goal"><Target size={16} aria-hidden="true" />
            <span><strong>{g.title}</strong> · <span className="num">{eur(g.saved, true)} of {eur(g.target, true)} by {month(g.deadline)}</span></span></p>
        ))}
        {seen.length > 0 && (
          <div>
            <h3 className="tour-sub">What Autopilot saw</h3>
            <div className="list tour-seen">
              {seen.map((t, i) => (
                <div className="row" key={i}>
                  <div className="row-main"><div>{t.counterparty}</div><div className="meta">{day(t.day)}</div></div>
                  <span className={`row-amount num${t.amount > 0 ? " in" : ""}`}>{t.amount > 0 ? "+" : "−"}{eur(Math.abs(t.amount))}</span>
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
        <button className="btn secondary" onClick={() => onGo(step - 1)} disabled={step === 0}><ArrowLeft size={18} /> Back</button>
        {step < STEPS.length - 1
          ? <button className="btn" onClick={() => onGo(step + 1)}>Next <ArrowRight size={18} /></button>
          : <button className="btn secondary" onClick={onRestart} disabled={busy}><RotateCcw size={18} /> Restart</button>}
      </div>
    </aside>
  );
}
