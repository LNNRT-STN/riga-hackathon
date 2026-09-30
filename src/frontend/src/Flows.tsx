import { useState } from "react";
import { ChevronLeft, ChevronRight, CircleCheck, Info, UserRound } from "lucide-react";
import type { Card, Customer, Option, Result } from "./api";
import { day, eur, TODAY } from "./format";

const place = (c: Customer, where?: string) => {
  if (where === "current") return "KBC-Plus Account";
  if (where === "savings") return "Savings account";
  if (where === "term") return "12-month KBC term account";
  if (where?.startsWith("goal:")) return `Savings for ${c.goals.find((g) => g.id === Number(where.slice(5)))?.title ?? "your goal"}`;
  return where ?? "";
};

export function PageBar({ title, onBack }: { title: string; onBack?: () => void }) {
  return (
    <div className={`pagebar${onBack ? "" : " root"}`}>
      {onBack && <button className="icon-btn" onClick={onBack} aria-label="Back"><ChevronLeft size={24} /></button>}
      <h1>{title}</h1>
    </div>
  );
}

/** "Why am I seeing this?": evidence in plain words, no model internals. */
export function Why({ card, onSettings }: { card: Card; onSettings: () => void }) {
  return (
    <>
      <div>
        <h3 className="small muted" style={{ marginBottom: 8 }}>What Autopilot noticed</h3>
        <ul className="evidence">{card.why.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
      </div>
      <dl className="facts">
        <div><dt>How sure we are</dt><dd>{card.why.confidence}</dd></div>
        <div><dt>Checked by</dt><dd>{card.why.checked_by}</dd></div>
        <div><dt>Estimated value for you</dt><dd className="num">{eur(card.why.customer_eur)} / year</dd></div>
        {card.goal && <div><dt>Linked to your goal</dt><dd>{card.goal.title}</dd></div>}
      </dl>
      <div className="msg info">
        <Info size={18} />
        <span>
          Autopilot compares every possible suggestion with doing nothing. This one was worth your attention;
          most days, nothing is. {card.includes_kbc_product && "It includes a KBC product because it compares honestly with non-KBC options."}
        </span>
      </div>
      <button className="btn secondary block" onClick={onSettings}>What Autopilot may use</button>
    </>
  );
}

export function Options({ card, onPick }: { card: Card; onPick: (o: Option) => void }) {
  return (
    <>
      <p className="small muted">{card.body}</p>
      {card.options.map((o) => (
        <button key={o.id} className="option" onClick={() => onPick(o)}>
          <span className="option-head">
            <span>{o.label}</span>
            <ChevronRight size={18} color="var(--text-muted)" />
          </span>
          {o.detail && <span className="small muted">{o.detail}</span>}
          <span style={{ display: "flex", gap: 6, marginTop: 4 }}>
            {o.kbc && <span className="badge product">KBC product</span>}
            {o.type === "handoff" && <span className="badge"><UserRound size={12} /> With a person</span>}
          </span>
        </button>
      ))}
      <p className="meta">Doing nothing is fine too. Close this to keep things as they are.</p>
    </>
  );
}

/** Review step before anything happens. Transfers and forms are simulated and labelled as such. */
export function Review({ c, card, option, busy, onConfirm, onCancel }: {
  c: Customer; card: Card; option: Option; busy: boolean;
  onConfirm: (always: boolean) => void; onCancel: () => void;
}) {
  const [always, setAlways] = useState(false);
  const transfer = option.type === "transfer";
  const maturity = card.situation_id === "maturity";
  return (
    <>
      <PageBar title={transfer ? "Review transfer" : "Review form"} onBack={onCancel} />
      <div className="screen" style={{ display: "grid", gap: 16, alignContent: "start" }}>
        <span className="badge sim" style={{ justifySelf: "start" }}>Simulated · no real money moves</span>
        {transfer ? (
          <>
            <div>
              <div className="meta">Amount</div>
              <div className="balance num" style={{ marginTop: 0 }}>{eur(option.amount ?? 0)}</div>
            </div>
            <dl className="facts">
              <div><dt>From</dt><dd>{place(c, option.from)}</dd></div>
              <div><dt>To</dt><dd>{place(c, option.to)}</dd></div>
              <div><dt>Date</dt><dd>{maturity ? "On the maturity date" : day(TODAY)}</dd></div>
              <div><dt>Fees</dt><dd className="num">{eur(0)}</dd></div>
            </dl>
          </>
        ) : (
          <>
            <h2 className="section-title" style={{ margin: 0 }}>{option.label}</h2>
            <dl className="facts">
              {Object.entries(option.fields ?? {}).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
            </dl>
            {option.detail && <p className="small muted">{option.detail}</p>}
          </>
        )}
        {option.always && (
          <label className="check">
            <input type="checkbox" checked={always} onChange={(e) => setAlways(e.target.checked)} />
            <span>
              <strong>Always do this</strong><br />
              Every month, keep {eur(option.always.keep)} on your current account and move the rest to this goal,
              at most {eur(option.always.cap)}. You can switch it off any time in Autopilot.
            </span>
          </label>
        )}
        <div style={{ display: "grid", gap: 8 }}>
          <button className="btn block" disabled={busy} onClick={() => onConfirm(always)}>
            {busy ? "Working on it" : transfer ? "Confirm transfer" : "Send form"}
          </button>
          <button className="btn secondary block" disabled={busy} onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </>
  );
}

export function Done({ result, onHome, onAutopilot }: { result: Result; onHome: () => void; onAutopilot: () => void }) {
  const title = { transfer: "Done", form: "Form sent", handoff: "An advisor will call you", info: "Noted" }[result.type] ?? "Done";
  return (
    <>
      <PageBar title={title} onBack={onHome} />
      <div className="screen" style={{ display: "grid", gap: 16, alignContent: "start" }}>
        <div className="msg success" role="status">
          <CircleCheck size={20} />
          <div style={{ display: "grid", gap: 6 }}>{result.lines.map((l, i) => <span key={i}>{l}</span>)}</div>
        </div>
        <button className="btn block" onClick={onHome}>Back to Start</button>
        <button className="btn secondary block" onClick={onAutopilot}>Open Autopilot</button>
      </div>
    </>
  );
}
