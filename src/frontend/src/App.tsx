import { useCallback, useEffect, useRef, useState } from "react";
import { ChartColumn, Compass, Cpu, House, LayoutGrid, ListOrdered, RotateCcw, Smartphone } from "lucide-react";
import { toast, Toaster } from "sonner";
import { api, type Card, type Customer, type Notification, type Option, type Result } from "./api";
import { Autopilot } from "./Autopilot";
import { BehindTheScenes } from "./BehindTheScenes";
import { Done, Options, Review, Why } from "./Flows";
import { Onboarding } from "./Onboarding";
import { Pipeline } from "./Pipeline";
import { NotificationBanner, Scenarios } from "./Scenarios";
import { Sheet } from "./Sheet";
import { Start } from "./Start";
import { STEPS, Tour, type Person, type TourStep } from "./Tour";

type View =
  | { name: "start" | "autopilot" | "onboarding" }
  | { name: "review"; card: Card; option: Option }
  | { name: "done"; result: Result }
  | { name: "tab"; tab: string };

type Pending = Pick<TourStep, "view" | "note">;

// The visitor's own try-out customer survives a reload in this tab. Storage can throw (private mode, blocked).
const TRY_KEY = "kbc-try-id";
const readTry = () => { try { return Number(sessionStorage.getItem(TRY_KEY)) || null; } catch { return null; } };
const writeTry = (v: number | null) => {
  try { if (v) sessionStorage.setItem(TRY_KEY, String(v)); else sessionStorage.removeItem(TRY_KEY); } catch { /* ignore */ }
};
// Where the jury is in the tour, also per tab.
const STEP_KEY = "kbc-tour-step";
const readStep = () => { try { return Math.min(STEPS.length - 1, Number(sessionStorage.getItem(STEP_KEY)) || 0); } catch { return 0; } };
const writeStep = (v: number) => { try { sessionStorage.setItem(STEP_KEY, String(v)); } catch { /* ignore */ } };
const FIRST = STEPS[0].who as number;

export function App() {
  const [people, setPeople] = useState<Person[]>([]);
  const [tryId, setTryId] = useState<number | null>(readTry);
  const [step, setStep] = useState(readStep);
  const [id, setId] = useState(() => {
    const w = STEPS[step].who;
    return (w === "try" ? tryId : w) ?? tryId ?? FIRST;
  });
  // View and notification the tour wants once the next customer has loaded.
  const pending = useRef<Pending | null>({ view: STEPS[step].view, note: STEPS[step].note });
  const [note, setNote] = useState<Notification | null>(null);
  const [c, setC] = useState<Customer | null>(null);
  const [view, setView] = useState<View>({ name: "start" });
  const [sheet, setSheet] = useState<null | "why" | "options" | "pipeline">(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phone, setPhone] = useState<HTMLDivElement | null>(null);
  const [engine, setEngine] = useState(() => !!STEPS[step].engine);

  const load = useCallback(async (cid: number) => {
    setError(null);
    try {
      const data = await api.customer(cid);
      setC(data);
      const p = pending.current;
      pending.current = null;
      setView(p?.view ? { name: p.view } : data.onboarded ? { name: "start" } : { name: "onboarding" });
      if (p?.note) setNote(p.note);
    } catch (e) {
      // A stored try-out id may be gone (demo reset, server restart): forget it and fall back to the first persona.
      if (cid === readTry()) { writeTry(null); setTryId(null); setId(FIRST); return; }
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => { api.customers().then(setPeople).catch((e) => setError(e.message)); }, []);
  useEffect(() => { setSheet(null); setNote(null); toast.dismiss(); load(id); }, [id, load]);

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    try { return await fn(); } catch (e) { toast.error((e as Error).message); } finally { setBusy(false); }
  }

  const approve = (card: Card, option?: Option, always = false) => run(async () => {
    const r = await api.respond(id, { instance_key: card.instance_key, response: "approve", option_id: option?.id, always });
    setC(r.view);
    setSheet(null);
    setView({ name: "done", result: r.result });
  });

  const respond = (card: Card, response: "later" | "not_relevant") => run(async () => {
    const r = await api.respond(id, { instance_key: card.instance_key, response });
    setC(r.view);
    toast(response === "later" ? "Snoozed for a week." : "Got it. Autopilot won't suggest this again.", {
      description: "You can change this under Autopilot → What Autopilot learned.",
    });
  });

  function primary(card: Card) {
    if (card.action === "options" || card.action === "handoff") return setSheet("options");
    const option = card.options[0];
    if (option && (option.type === "transfer" || option.type === "form")) return setView({ name: "review", card, option });
    approve(card, option);
  }

  function pick(card: Card, option: Option) {
    if (option.type === "transfer" || option.type === "form") {
      setSheet(null);
      return setView({ name: "review", card, option });
    }
    approve(card, option);
  }

  const settings = (s: Parameters<typeof api.settings>[1]) => run(async () => setC(await api.settings(id, s)));

  const tryIt = () => run(async () => {
    const you = await api.try();
    writeTry(you.id);
    setTryId(you.id);
    setEngine(false);
    pending.current = { view: "onboarding" };
    setId(you.id);
  });

  function go(i: number) {
    const s = STEPS[i];
    setStep(i);
    writeStep(i);
    setEngine(!!s.engine);
    const target = s.who === "try" ? tryId : s.who;
    if (!target) return;
    if (target !== id) { pending.current = { view: s.view, note: s.note }; return setId(target); }
    setSheet(null);
    setNote(s.note ?? null);
    if (s.view) setView({ name: s.view });
  }

  function pickCustomer(cid: number) {
    setEngine(false);
    if (cid === id) return setView(c?.onboarded ? { name: "start" } : { name: "onboarding" });
    pending.current = null;
    setId(cid);
  }

  const scenario = (sid: string) => run(async () => {
    const r = await api.scenario(id, sid);
    setC(r.view);
    toast.dismiss();
    if (r.notification) return setNote(r.notification);
    const narrow = !window.matchMedia("(min-width: 1000px)").matches;
    toast("Autopilot stayed quiet — see why in How Autopilot decided",
      narrow ? { action: { label: "Show", onClick: () => setSheet("pipeline") } } : undefined);
  });

  function openNote() {
    setNote(null);
    if (c && !c.onboarded) return setView({ name: "onboarding" });   // the tour's goal suggestion
    setView({ name: "start" });
    requestAnimationFrame(() => {
      // Scroll only the phone's screen, never the page around it.
      const h = document.getElementById("for-you");
      const screen = h?.closest<HTMLElement>(".screen");
      if (h && screen) screen.scrollTo({ top: h.offsetTop - screen.offsetTop - 8 });
      h?.focus({ preventScroll: true });
    });
  }

  async function resetDemo() {
    await run(async () => {
      await api.resetDemo();
      await load(id);
      toast("Demo reset. All customers are back to their starting point.");
    });
  }

  const tabs = [["Start", House], ["My KBC", LayoutGrid], ["Invest", ChartColumn], ["Autopilot", Compass]] as const;
  const home = () => setView({ name: "start" });

  return (
    <>
      <header className="topbar-app">
        <div className="wordmark"><Compass size={22} /> KBC <span>Autopilot</span></div>
        <div className="shell-actions">
          <button className="btn secondary" onClick={() => setEngine(!engine)}>
            {engine ? <><Smartphone size={18} /> <span className="lbl-long">Back to the app</span><span className="lbl-short">App</span></> : <><Cpu size={18} /> <span className="lbl-long">Behind the scenes</span><span className="lbl-short">Engine</span></>}
          </button>
          <button className="icon-btn" onClick={resetDemo} aria-label="Reset demo" title="Reset demo" disabled={busy}><RotateCcw size={20} /></button>
        </div>
      </header>
      <p className="meta shell-intro">
        Synthetic customers. Every transfer, form and advisor call is simulated.
      </p>

      <div className={`stage${engine ? " wide" : ""}`}>
        <Tour step={step} c={c} people={people} tryId={tryId} busy={busy} onGo={go} onTry={tryIt} onPick={pickCustomer}
          onRestart={async () => { await resetDemo(); go(0); }} />
        {engine && <BehindTheScenes onBack={() => setEngine(false)} />}
        <div className="app-col" hidden={engine}>
          <div className="app" ref={setPhone}>
            {error && <div className="screen"><div className="msg danger" role="alert">{error}
              <button className="btn-text" onClick={() => load(id)}>Try again</button></div></div>}
            {!error && !c && <div className="screen"><p className="muted">Loading</p></div>}
            {!error && c && (
              <>
                {view.name === "start" && (
                  <Start key={c.id} c={c} busy={busy} onAutopilot={() => setView({ name: "autopilot" })} onPrimary={primary}
                    onRespond={respond} onWhy={() => setSheet("why")} />
                )}
                {view.name === "autopilot" && (
                  <Autopilot key={c.id} c={c} busy={busy} onUpdate={setC}
                    top={c.is_try && c.onboarded ? <Scenarios c={c} busy={busy} onRun={scenario} /> : undefined}
                    onEditPlan={() => setView({ name: "onboarding" })}
                    onSettings={settings} onResetMemory={() => run(async () => setC(await api.resetMemory(id)))}
                    onRevoke={(r) => run(async () => setC(await api.revokeRule(id, r)))} />
                )}
                {view.name === "onboarding" && (
                  <Onboarding key={c.id} c={c} onBack={home} notify={(m) => toast(m)}
                    onSaved={(fresh) => { setC(fresh); setView({ name: "autopilot" }); }} />
                )}
                {view.name === "review" && (
                  <Review c={c} card={view.card} option={view.option} busy={busy} onCancel={home}
                    onConfirm={(always) => approve(view.card, view.option, always)} />
                )}
                {view.name === "done" && <Done result={view.result} onHome={home} onAutopilot={() => setView({ name: "autopilot" })} />}
                {view.name === "tab" && (
                  <div className="screen"><div className="empty"><strong>{view.tab}</strong>
                    <span className="small muted">Not part of this prototype. Autopilot lives on Start.</span></div></div>
                )}
                {["start", "autopilot", "tab"].includes(view.name) && (
                  <nav className="tabbar" aria-label="Main">
                    {tabs.map(([label, Icon]) => {
                      const current = label === "Start" ? view.name === "start"
                        : label === "Autopilot" ? view.name === "autopilot" : view.name === "tab" && view.tab === label;
                      return (
                        <button key={label} className="tab" aria-current={current ? "page" : undefined}
                          onClick={() => setView(label === "Start" ? { name: "start" } : label === "Autopilot" ? { name: "autopilot" }
                            : { name: "tab", tab: label })}>
                          <Icon size={24} />{label}
                        </button>
                      );
                    })}
                  </nav>
                )}
                {note && <NotificationBanner note={note} onOpen={openNote} onDismiss={() => setNote(null)} />}
                <Sheet title="How Autopilot decided" open={sheet === "pipeline"} onClose={() => setSheet(null)} container={phone}>
                  <Pipeline c={c} />
                </Sheet>
                {c.card && (
                  <>
                    <Sheet title="Why am I seeing this?" open={sheet === "why"} onClose={() => setSheet(null)} container={phone}>
                      <Why card={c.card} onSettings={() => { setSheet(null); setView({ name: "autopilot" }); }} />
                    </Sheet>
                    <Sheet title="Your options" open={sheet === "options"} onClose={() => setSheet(null)} container={phone}>
                      <Options card={c.card} onPick={(o) => pick(c.card!, o)} />
                    </Sheet>
                  </>
                )}
              </>
            )}
            <Toaster position="top-center" richColors={false} toastOptions={{ style: { fontFamily: "inherit" } }} />
          </div>
          <button className="btn-text decided-open" onClick={() => setSheet("pipeline")} disabled={!c}>
            <ListOrdered size={18} /> How Autopilot decided
          </button>
        </div>
      </div>
    </>
  );
}
