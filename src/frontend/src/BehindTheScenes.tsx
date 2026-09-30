import { useEffect, useState } from "react";
import { ArrowRight, ChevronLeft, Code, Search, Sparkles } from "lucide-react";
import { api, type Engine, type Screened } from "./api";
import { eur } from "./format";

const nf = new Intl.NumberFormat("nl-BE");

/** For the jury: the same engine over every synthetic customer, the catalogue, and a live new situation. */
export function BehindTheScenes({ onBack }: { onBack: () => void }) {
  const [data, setData] = useState<Engine | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [screened, setScreened] = useState<Screened | null>(null);

  useEffect(() => { api.engine().then(setData).catch((e) => setError(e.message)); }, []);

  async function screen(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try { setScreened(await api.addSituation(text)); } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }

  if (!data) return <main className="bts"><p className="muted">{error ?? "Running the engine over 2.000 customers"}</p></main>;
  const f = data.funnel;
  const k = f.scale / f.customers;
  const q = data.catalogue.find((s) => s.question)?.question?.replace("{text}", "…") ?? "";
  const stages = [
    { ai: false, tech: "Python", title: "Spot", text: "Plain rules read each customer's own transactions and goals.",
      code: "for s in SITUATIONS:\n  s.detect(features)", n: f.with_candidate, unit: "have a possible situation" },
    { ai: true, tech: "Jev", title: "Check", text: "Where rules can't tell, Jev answers one typed yes/no question.",
      code: `${q}\n→ yes · 0,93`, n: f.confirmed, unit: "confirmed" },
    { ai: false, tech: "Python", title: "Decide", text: "Money maths in code. The card must beat doing nothing.",
      code: "€ for customer\n× goal weight\n× confidence\n− annoyance\n> do-nothing bar", n: f.shown, unit: "shown one card" },
    { ai: true, tech: "LLM", title: "Word", text: "An LLM rewrites the card in plain words. Amounts are locked.",
      code: "every € amount kept?\nno pushy words?\nelse: use the template", n: f.shown, unit: "cards worded" },
  ];
  const maxShown = Math.max(...f.situations.map((s) => s.shown), 1);

  return (
    <main className="bts">
      <button className="btn-text" onClick={onBack} style={{ paddingLeft: 0 }}><ChevronLeft size={18} /> Back to the app</button>
      <h1 className="bts-title">Behind the scenes</h1>
      <p className="muted" style={{ maxWidth: "68ch" }}>
        One engine, no segments. Every customer is checked against every situation in the catalogue; a card is shown only when
        its value for the customer beats doing nothing. All numbers below are live from {nf.format(f.customers)} synthetic customers
        (AI: {f.ai_mode}).
      </p>

      <section className="panel how" aria-labelledby="how-title">
        <div className="how-head">
          <h2 id="how-title" className="section-title">How it works</h2>
          <span className="meta"><span className="tech"><Code size={14} /> Python</span> is code, <span className="tech ai"><Sparkles size={14} /> AI</span> only
            answers or rewords</span>
        </div>
        <ol className="flow">
          {stages.map((st, i) => (
            <li key={st.title} className={st.ai ? "ai" : undefined}>
              <span className={`tech${st.ai ? " ai" : ""}`}>{st.ai ? <Sparkles size={14} /> : <Code size={14} />} {st.tech}</span>
              <h3>{st.title}</h3>
              <p className="small">{st.text}</p>
              <code>{st.code}</code>
              <p className="flow-n"><strong className="num">{nf.format(st.n)}</strong> <span className="meta">{st.unit}</span></p>
              {i < stages.length - 1 && <ArrowRight className="flow-arrow" size={20} aria-hidden="true" />}
            </li>
          ))}
        </ol>
        <p className="small muted how-foot">
          Of {nf.format(f.customers)} synthetic customers, <strong>{Math.round((1 - f.shown / f.customers) * 100)}% are left alone on purpose</strong>.
          No AI key? Keyword checks and templates take over, so every step still runs.
        </p>
      </section>

      <section className="bts-grid">
        <div className="panel">
          <h2 className="section-title">Cards shown per situation</h2>
          {f.situations.map((s) => (
            <div key={s.id} className="bar-row">
              <div className="bar-head"><span>{s.name} <span className={`badge ${s.kind === "product" ? "product" : ""}`}>{s.kind}</span></span>
                <strong className="num">{nf.format(s.shown)}</strong></div>
              <div className="bar"><span style={{ width: `${(s.shown / maxShown) * 100}%` }} /></div>
            </div>
          ))}
          <p className="small muted" style={{ marginTop: 12 }}>
            Help first: {nf.format(f.help)} help cards for {nf.format(f.product)} that include a KBC product.
          </p>
        </div>

        <div className="panel">
          <h2 className="section-title">At 2,3 million customers</h2>
          <dl className="facts">
            <div><dt>Value for customers (cards shown now)</dt><dd className="num">{eur(f.customer_eur * k, true)} / year</dd></div>
            <div><dt>Value for KBC, if accepted</dt><dd className="num">{eur(f.kbc_eur * k, true)} / year</dd></div>
            <div><dt>Cards where KBC deliberately earns nothing</dt><dd className="num">{nf.format(Math.round(f.trust * k))}</dd></div>
            <div><dt>AI cost (screening + wording)</dt><dd className="num">≈ $ {nf.format(Math.round(f.cost_per_day_usd))} / day</dd></div>
          </dl>
          <p className="meta" style={{ marginTop: 8 }}>
            Estimates from synthetic data. {nf.format(f.holdout)} customers form a holdout group that only gets urgent warnings
            ({nf.format(f.holdout_shown)} did); comparing them with everyone else is how a real pilot measures the effect.
          </p>
        </div>
      </section>

      <section className="panel" style={{ marginTop: 24 }}>
        <h2 className="section-title">Add a situation in plain language</h2>
        <p className="small muted">No code. Autopilot asks one yes/no question per customer over a sample of 200 and shows who matches.</p>
        <form className="composer" style={{ padding: "12px 0 0" }} onSubmit={screen}>
          <label htmlFor="sit" className="sr-only">Situation</label>
          <input id="sit" value={text} onChange={(e) => setText(e.target.value)} maxLength={200}
            placeholder="E.g. customer recently got a pet" />
          <button className="btn" disabled={busy || text.trim().length < 4}><Search size={18} /> {busy ? "Checking" : "Check customers"}</button>
        </form>
        {error && <div className="msg danger" style={{ marginTop: 12 }}>{error}</div>}
        {screened && (
          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            <div className="msg success"><span><strong>{screened.matches} of {screened.sample} customers match “{screened.text}”</strong>
              About {nf.format(screened.estimate)} KBC customers at scale ({screened.source === "jev" ? "AI check" : "offline keyword fallback"}).</span></div>
            {screened.examples.map((x) => (
              <div key={x.customer} className="small"><strong className="num">{x.customer}</strong> · {x.evidence.join(" · ") || "matched by the AI check"}</div>
            ))}
            <p className="meta">Next step in real life: a content designer writes the card, then it goes live for everyone it applies to.</p>
          </div>
        )}
      </section>

      <section className="panel" style={{ marginTop: 24 }}>
        <h2 className="section-title">The catalogue: one row per situation</h2>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Situation</th><th>Helps</th><th>Kind</th><th>How it's detected</th><th>Action</th></tr></thead>
            <tbody>
              {data.catalogue.map((s) => (
                <tr key={s.id}>
                  <td><strong>{s.name}</strong>{s.risk === "critical" && <span className="badge off" style={{ marginLeft: 6 }}>urgent</span>}</td>
                  <td>{s.audience}</td>
                  <td><span className={`badge ${s.kind === "product" ? "product" : ""}`}>{s.kind}</span></td>
                  <td>{s.check}{s.question && <div className="meta">“{s.question}”</div>}</td>
                  <td>{s.action}</td>
                </tr>
              ))}
              {data.custom.map((s, i) => (
                <tr key={`c${i}`}><td><strong>{s.text}</strong></td><td>Added live</td><td><span className="badge">screening</span></td>
                  <td>AI yes/no check · {s.matches}/{s.sample} matched</td><td>card to be written</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
