import { useCallback, useEffect, useState } from "react";
import { ChartColumn, Compass, Cpu, House, LayoutGrid, RotateCcw, Smartphone, Tag } from "lucide-react";
import { toast, Toaster } from "sonner";
import { api, type Card, type Customer, type Option, type Result } from "./api";
import { Autopilot } from "./Autopilot";
import { BehindTheScenes } from "./BehindTheScenes";
import { Done, Options, Review, Why } from "./Flows";
import { Onboarding } from "./Onboarding";
import { Sheet } from "./Sheet";
import { Start } from "./Start";

type View =
  | { name: "start" }
  | { name: "autopilot" }
  | { name: "onboarding" }
  | { name: "review"; card: Card; option: Option }
  | { name: "done"; result: Result }
  | { name: "tab"; tab: string };

type Person = { id: number; name: string; persona: string };

export function App() {
  const [people, setPeople] = useState<Person[]>([]);
  const [id, setId] = useState(1);
  const [c, setC] = useState<Customer | null>(null);
  const [view, setView] = useState<View>({ name: "start" });
  const [sheet, setSheet] = useState<null | "why" | "options">(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phone, setPhone] = useState<HTMLDivElement | null>(null);
  const [engine, setEngine] = useState(false);

  const load = useCallback(async (cid: number) => {
    setError(null);
    try {
      const data = await api.customer(cid);
      setC(data);
      setView(data.onboarded ? { name: "start" } : { name: "onboarding" });
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => { api.customers().then(setPeople).catch((e) => setError(e.message)); }, []);
  useEffect(() => { setSheet(null); load(id); }, [id, load]);

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

  async function resetDemo() {
    await run(async () => {
      await api.resetDemo();
      await load(id);
      toast("Demo reset. All customers are back to their starting point.");
    });
  }

  const tabs = [["Start", House], ["My KBC", LayoutGrid], ["Invest", ChartColumn], ["Offers", Tag]] as const;
  const home = () => setView({ name: "start" });

  return (
    <div className={`stage${engine ? " wide" : ""}`}>
      <aside className="jury" aria-label="Demo controls">
        <div className="wordmark"><Compass size={22} /> KBC <span>Autopilot</span></div>
        <p className="jury-intro">
          A proof of concept inside a KBC-style banking app. You say where you want to go; Autopilot watches for
          situations that matter to your goals and shows one card only when it clearly helps.
        </p>
        <div className="people" role="group" aria-label="Open a demo customer">
          {people.map((p) => (
            <button key={p.id} className="person" aria-pressed={!engine && p.id === id} onClick={() => { setEngine(false); setId(p.id); }}>
              <span className="avatar" aria-hidden="true">{p.name.slice(0, 2).toUpperCase()}</span>
              <span><strong>{p.name}</strong><span className="meta">{p.persona}</span></span>
            </button>
          ))}
        </div>
        <div className="jury-select">
          <label htmlFor="who" className="sr-only">Demo customer</label>
          <select id="who" value={id} onChange={(e) => setId(Number(e.target.value))}>
            {people.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.persona}</option>)}
          </select>
          <button className="icon-btn" onClick={resetDemo} aria-label="Reset demo" disabled={busy}><RotateCcw size={20} /></button>
        </div>
        <div className="jury-foot">
          <button className="btn" onClick={() => setEngine(!engine)}>
            {engine ? <><Smartphone size={18} /> Back to the app</> : <><Cpu size={18} /> Behind the scenes</>}
          </button>
          <button className="btn secondary" onClick={resetDemo} disabled={busy}><RotateCcw size={18} /> Reset demo</button>
          <p className="meta">Synthetic customers. Every transfer, form and advisor call is simulated.</p>
        </div>
      </aside>

      {engine && <BehindTheScenes onBack={() => setEngine(false)} />}
      <div className="phone" ref={setPhone} hidden={engine}>
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
              <Autopilot key={c.id} c={c} busy={busy} onBack={home} onEditPlan={() => setView({ name: "onboarding" })}
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
            {["start", "tab"].includes(view.name) && (
              <nav className="tabbar" aria-label="Main">
                {tabs.map(([label, Icon]) => {
                  const current = label === "Start" ? view.name === "start" : view.name === "tab" && view.tab === label;
                  return (
                    <button key={label} className="tab" aria-current={current ? "page" : undefined}
                      onClick={() => setView(label === "Start" ? { name: "start" } : { name: "tab", tab: label })}>
                      <Icon size={24} />{label}
                    </button>
                  );
                })}
              </nav>
            )}
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
    </div>
  );
}
