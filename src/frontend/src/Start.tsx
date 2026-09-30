import { ArrowDownLeft, ArrowUpRight, Bell, CircleHelp, Compass, Info, Target, TriangleAlert } from "lucide-react";
import type { Card, Customer } from "./api";
import { day, eur } from "./format";

export function Start({ c, onAutopilot, onPrimary, onRespond, onWhy, busy }: {
  c: Customer;
  onAutopilot: () => void;
  onPrimary: (card: Card) => void;
  onRespond: (card: Card, response: "later" | "not_relevant") => void;
  onWhy: () => void;
  busy: boolean;
}) {
  return (
    <>
      <header className="topbar">
        <span className="avatar" aria-hidden="true">{c.name.slice(0, 2).toUpperCase()}</span>
        <button className="kate" type="button" disabled title="Kate chat is not part of this prototype">
          <CircleHelp size={18} /> How can I help?
        </button>
        <button className="icon-btn" type="button" aria-label="Notifications" disabled><Bell size={22} /></button>
      </header>
      <div className="screen">
        <nav className="chips" aria-label="Topics">
          <button className="chip" type="button" onClick={onAutopilot}><Compass size={16} /> Autopilot</button>
          <span className="chip inert">MyHome</span>
          <span className="chip inert">MyMobility</span>
        </nav>

        <section aria-label="Accounts" style={{ marginTop: 12 }}>
          <div className="accounts">
            <article className="account">
              <div className="account-band" />
              <div className="account-body">
                <div className="account-name">KBC-Plus Account</div>
                <div className="meta num">BE68 •••• •••• 4412</div>
                <div className="balance num">{eur(c.balance)}</div>
              </div>
            </article>
            <article className="account">
              <div className="account-band savings" />
              <div className="account-body">
                <div className="account-name">Savings account</div>
                <div className="meta num">BE21 •••• •••• 0937</div>
                <div className="balance num">{eur(c.savings)}</div>
              </div>
            </article>
          </div>
        </section>

        <section aria-labelledby="for-you">
          <h2 className="section-title" id="for-you" tabIndex={-1}>For you</h2>
          {c.card ? (
            <Tip card={c.card} busy={busy} onPrimary={onPrimary} onRespond={onRespond} onWhy={onWhy} />
          ) : (
            <div className="empty">
              <strong style={{ color: "var(--navy)" }}>Nothing needs your attention</strong>
              <span className="small muted">Autopilot keeps watching and only speaks up when it clearly helps. That's the point.</span>
              <button className="btn-text" style={{ justifySelf: "start", paddingLeft: 0 }} onClick={onAutopilot}>
                See what Autopilot checked
              </button>
            </div>
          )}
        </section>
        <section>
          <h2 className="section-title">Recent transactions</h2>
          <div className="list">
            {c.transactions.slice(0, 5).map((t, i) => (
              <div className="row" key={i}>
                <span className="row-icon">{t.amount > 0 ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</span>
                <div className="row-main">
                  <div>{t.counterparty}</div>
                  <div className="meta">{day(t.day)}</div>
                </div>
                <span className={`row-amount num${t.amount > 0 ? " in" : ""}`}>{t.amount > 0 ? "+" : "−"}{eur(Math.abs(t.amount))}</span>
              </div>
            ))}
          </div>
        </section>

      </div>
    </>
  );
}

function Tip({ card, busy, onPrimary, onRespond, onWhy }: {
  card: Card; busy: boolean;
  onPrimary: (card: Card) => void;
  onRespond: (card: Card, response: "later" | "not_relevant") => void;
  onWhy: () => void;
}) {
  const critical = card.risk === "critical";
  return (
    <article className={`tip${critical ? " critical" : ""}`} aria-live="polite">
      <div className="tip-label">
        {critical ? <TriangleAlert size={16} /> : <Compass size={16} />}
        {critical ? "Autopilot heads-up" : "Autopilot tip"}
        {card.includes_kbc_product && <span className="badge product">Includes a KBC product</span>}
      </div>
      <div style={{ display: "grid", gap: 4 }}>
        <h3>{card.title}</h3>
        <p>{card.body}</p>
      </div>
      <div className="benefit">{card.benefit}</div>
      {card.goal && (
        <div className="goal-link">
          <div className="goal-link-head">
            <span><Target size={14} style={{ verticalAlign: -2, marginRight: 6 }} />This helps: <strong>{card.goal.title}</strong></span>
            <span className="num muted">{eur(card.goal.saved, true)} / {eur(card.goal.target, true)}</span>
          </div>
          <div className="progress" aria-hidden="true">
            <span style={{ width: `${Math.min(100, (card.goal.saved / card.goal.target) * 100)}%` }} />
          </div>
        </div>
      )}
      <div className="tip-actions">
        <button className="btn" disabled={busy} onClick={() => onPrimary(card)}>{card.primary}</button>
        <button className="btn-text" disabled={busy} onClick={() => onRespond(card, "later")}>Later</button>
        <button className="btn-text quiet" disabled={busy} onClick={() => onRespond(card, "not_relevant")}>Not relevant</button>
      </div>
      <div className="tip-foot">
        <button className="btn-text" style={{ paddingLeft: 0 }} onClick={onWhy}><Info size={16} /> Why am I seeing this?</button>
        <span className="meta">Doing nothing is fine too.</span>
      </div>
    </article>
  );
}
