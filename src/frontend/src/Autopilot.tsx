import { useState, type ReactNode } from "react";
import { Accordion, Switch, ToggleGroup } from "radix-ui";
import { ChevronDown, Plus, RotateCcw, Target } from "lucide-react";
import { toast } from "sonner";
import { api, type Customer, type DraftGoal, type Suggestion } from "./api";
import { GoalRows, Route, type PlanGoal } from "./FlightPlan";
import { PageBar } from "./Flows";
import { day, eur, month } from "./format";

const MODES = {
  quiet: "Only when it's worth at least € 50 a year, or urgent.",
  normal: "When it's worth about € 15 a year or more.",
  proactive: "Small wins too, from about € 3 a year.",
} as const;

export function Autopilot({ c, busy, top, onEditPlan, onUpdate, onSettings, onResetMemory, onRevoke }: {
  c: Customer; busy: boolean;
  top?: ReactNode;
  onEditPlan: () => void;
  onUpdate: (c: Customer) => void;
  onSettings: (s: Partial<Pick<Customer, "mode" | "consent_help" | "consent_product">>) => void;
  onResetMemory: () => void;
  onRevoke: (rule: number) => void;
}) {
  const goals: PlanGoal[] = c.goals;
  const [pending, setPending] = useState(false);
  const addGoal = (s: Suggestion) => {
    const goal: DraftGoal = { title: s.title, type: s.type, horizon: s.horizon, target_eur: s.target_eur, deadline: s.deadline,
                              priority: goals.length + 1, monthly_eur: 0 };
    setPending(true);
    api.addGoal(c.id, goal).then(onUpdate).catch((e: Error) => toast.error(e.message)).finally(() => setPending(false));
  };
  return (
    <>
      <PageBar title="Autopilot" />
      <div className="screen">
        {top}
        {c.suggestions.length > 0 && goals.length < 5 && (
          <section aria-labelledby="suggested-paths">
            <h2 className="section-title" id="suggested-paths">Autopilot suggests</h2>
            <div className="list">
              {c.suggestions.map((s) => (
                <div className="row suggestion" key={s.key}>
                  <div className="row-main wrap">
                    <div><strong>{s.title}</strong></div>
                    <div className="meta num">{eur(s.target_eur, true)} by {month(s.deadline)}</div>
                    <div className="small muted">{s.reason}</div>
                  </div>
                  <button className="btn secondary" type="button" disabled={busy || pending} onClick={() => addGoal(s)}><Plus size={16} /> Add</button>
                </div>
              ))}
            </div>
          </section>
        )}
        <section>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 className="section-title" style={{ margin: 0 }}>Your goals</h2>
            <button className="btn-text" onClick={onEditPlan}><Target size={16} /> {goals.length ? "Edit" : "Set goals"}</button>
          </div>
          {goals.length ? (
            <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
              <Route goals={goals} />
              <GoalRows goals={goals} />
            </div>
          ) : (
            <div className="empty" style={{ marginTop: 8 }}>
              <strong style={{ color: "var(--navy)" }}>Where do you want to fly to?</strong>
              <span className="small muted">Set your goals in two minutes. Autopilot then looks out for what gets you there.</span>
              <button className="btn" style={{ justifySelf: "start", marginTop: 8 }} onClick={onEditPlan}>Set my goals</button>
            </div>
          )}
        </section>

        <section>
          <h2 className="section-title">What you accepted so far</h2>
          <div className="list"><div className="row">
            <div className="row-main wrap"><div className="small muted">Estimated value of the suggestions you accepted</div></div>
            <strong className="num" style={{ color: "var(--navy)" }}>{eur(c.value_created)} / year</strong>
          </div></div>
        </section>

        {c.rules.length > 0 && (
          <section>
            <h2 className="section-title">Rules you switched on</h2>
            <div className="list">
              {c.rules.map((r) => (
                <div className="row" key={r.id}>
                  <div className="row-main">
                    <div style={{ whiteSpace: "normal" }}>Keep {eur(r.keep)}, move the rest to {r.goal} (max {eur(r.cap)} a month)</div>
                    <div className="meta">Next run {day(r.next_run)} · at today's balance: {eur(r.preview)}</div>
                  </div>
                  <button className="btn-text" disabled={busy} onClick={() => onRevoke(r.id)}>Switch off</button>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <h2 className="section-title" id="mode-label">How often may Autopilot speak up?</h2>
          <ToggleGroup.Root type="single" className="segmented" aria-labelledby="mode-label" value={c.mode}
            onValueChange={(v) => v && onSettings({ mode: v as Customer["mode"] })} disabled={busy}>
            <ToggleGroup.Item value="quiet">Quiet</ToggleGroup.Item>
            <ToggleGroup.Item value="normal">Normal</ToggleGroup.Item>
            <ToggleGroup.Item value="proactive">Proactive</ToggleGroup.Item>
          </ToggleGroup.Root>
          <p className="small muted" style={{ marginTop: 8 }}>{MODES[c.mode]}</p>
        </section>

        <section>
          <h2 className="section-title">What Autopilot may use</h2>
          <div className="list">
            <Toggle id="help" checked={c.consent_help} disabled={busy} onChange={(v) => onSettings({ consent_help: v })}
              title="Helpful suggestions" text="Use my payments to spot problems and savings. (Extra gebruiksgemak)" />
            <Toggle id="product" checked={c.consent_product} disabled={busy} onChange={(v) => onSettings({ consent_product: v })}
              title="Suggestions that include KBC products" text="Always labelled and compared honestly. (Op jouw maat)" />
          </div>
        </section>

        <section>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 className="section-title" style={{ margin: 0 }}>What Autopilot learned</h2>
            {c.memory.length > 0 && (
              <button className="btn-text" disabled={busy} onClick={onResetMemory}><RotateCcw size={16} /> Reset</button>
            )}
          </div>
          <div className="list" style={{ marginTop: 8 }}>
            {c.memory.length ? c.memory.map((m, i) => <div className="row small" key={i}>{m}</div>)
              : <div className="row small muted">Nothing yet. Your answers to suggestions show up here, and you can reset them.</div>}
          </div>
        </section>

        <section>
          <Accordion.Root type="single" collapsible className="list">
            <Accordion.Item value="considered" className="acc-item">
              <Accordion.Header style={{ margin: 0 }}>
                <Accordion.Trigger className="acc-trigger">What Autopilot checked today <ChevronDown size={18} /></Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className="acc-content">
                <div className="row" style={{ padding: "8px 0", minHeight: 0 }}>
                  <div className="row-main"><strong>Do nothing</strong><div className="meta">The bar every suggestion has to beat in {c.mode} mode</div></div>
                  <span className="num">{eur(c.bar, true)}</span>
                </div>
                {c.considered.map((x, i) => (
                  <div className="row" key={i} style={{ padding: "8px 0", minHeight: 0 }}>
                    <div className="row-main"><div>{x.name}</div><div className="meta">{x.status_text}</div></div>
                    {x.score !== null && <span className={`num ${x.status === "shown" ? "" : "muted"}`}>{eur(Math.max(0, x.score), true)}</span>}
                  </div>
                ))}
              </Accordion.Content>
            </Accordion.Item>
            {c.log.length > 0 && (
              <Accordion.Item value="log" className="acc-item">
                <Accordion.Header style={{ margin: 0 }}>
                  <Accordion.Trigger className="acc-trigger">Activity <ChevronDown size={18} /></Accordion.Trigger>
                </Accordion.Header>
                <Accordion.Content className="acc-content">
                  {c.log.map((l, i) => <div key={i} className="row" style={{ padding: "8px 0", minHeight: 0 }}>
                    <div className="row-main"><div style={{ whiteSpace: "normal" }}>{l.text}</div><div className="meta">{day(l.day)}</div></div>
                  </div>)}
                </Accordion.Content>
              </Accordion.Item>
            )}
          </Accordion.Root>
          <p className="meta" style={{ marginTop: 8 }}>Scores are the estimated yearly value for you after subtracting how much a message would bother you. Updated {month("2026-09-30")}.</p>
        </section>
      </div>
    </>
  );
}

function Toggle({ id, title, text, checked, disabled, onChange }: {
  id: string; title: string; text: string; checked: boolean; disabled: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="switch-row">
      <label htmlFor={`sw-${id}`} style={{ cursor: "pointer" }}>
        <div style={{ fontWeight: 600, color: "var(--navy)" }}>{title}</div>
        <div className="small muted">{text}</div>
      </label>
      <Switch.Root id={`sw-${id}`} className="switch" checked={checked} disabled={disabled} onCheckedChange={onChange}>
        <Switch.Thumb className="switch-thumb" />
      </Switch.Root>
    </div>
  );
}
