import { useEffect, useState } from "react";
import { ChevronRight, Compass, X } from "lucide-react";
import { api, type Customer, type Notification, type Scenario } from "./api";

/** Try customers only: fast-forward into a situation and see whether Autopilot speaks up. */
export function Scenarios({ c, busy, onRun }: { c: Customer; busy: boolean; onRun: (id: string) => void }) {
  const [list, setList] = useState<Scenario[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { api.scenarios().then(setList).catch(() => setError(true)); }, []);
  const noGoals = c.goals.length === 0;

  return (
    <section aria-labelledby="next">
      <h2 className="section-title" id="next" style={{ marginBottom: 4 }}>What happens next?</h2>
      <p className="small muted" style={{ marginBottom: 12 }}>
        Fast-forward your month. Pick a moment and see whether Autopilot speaks up. Simulated.
      </p>
      {error && <p className="small muted">Couldn't load the moments. Reload the page to try again.</p>}
      {!error && !list && <p className="small muted">Loading</p>}
      {list && (
        <div className="list">
          {list.map((s) => {
            const locked = s.needs_goal && noGoals;
            return (
              <button key={s.id} type="button" className="row row-btn" disabled={busy || locked} onClick={() => onRun(s.id)}>
                <div className="row-main wrap">
                  <div style={{ fontWeight: 600, color: "var(--navy)" }}>{s.label}</div>
                  <div className="meta">{locked ? "Set a goal first: this one needs a goal to work towards." : s.blurb}</div>
                </div>
                <ChevronRight size={18} aria-hidden="true" />
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}

/** Lock-screen style banner inside the phone frame. Tap to open the card; it stays until opened or closed (WCAG 2.2.1). */
export function NotificationBanner({ note, onOpen, onDismiss }: {
  note: Notification; onOpen: () => void; onDismiss: () => void;
}) {
  return (
    <div className="notice-wrap" role="status">
      <button type="button" className="notice" onClick={onOpen}>
        <span className="notice-icon" aria-hidden="true"><Compass size={18} /></span>
        <span className="notice-text">
          <span className="meta">KBC Autopilot · now</span>
          <strong>{note.title}</strong>
          <span className="small">{note.body}</span>
        </span>
      </button>
      <button type="button" className="icon-btn notice-close" aria-label="Dismiss notification" onClick={onDismiss}><X size={18} /></button>
    </div>
  );
}
