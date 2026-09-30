import { CircleCheck, CircleX, Info } from "lucide-react";
import type { Customer, Step } from "./api";

const TONE = {
  ok: { Icon: CircleCheck, word: "Yes" },
  no: { Icon: CircleX, word: "No" },
  info: { Icon: Info, word: "Note" },
} as const;

/** The same seven steps for every customer: how Autopilot got from signals to one card, or to silence. */
export function Pipeline({ c }: { c: Customer }) {
  const steps: Step[] = c.pipeline ?? [];
  if (!steps.length) return <p className="small muted">No decision trace for this customer yet.</p>;
  const decision = steps[steps.length - 1];
  return (
    <>
    <p className="msg info" style={{ marginBottom: 16 }}><strong>{decision.summary}</strong></p>
    <ol className="steps">
      {steps.map((s, i) => (
        <li key={s.key} className={`step${s.key === "decision" ? " final" : ""}`}>
          <span className="step-num num" aria-hidden="true">{i + 1}</span>
          <div className="step-main">
            <h3>{s.title}</h3>
            <p className="small">{s.summary}</p>
            {s.items.length > 0 && (
              <details>
                <summary>Show details</summary>
                <ul className="step-items">
                  {s.items.map((it, j) => {
                    const { Icon, word } = TONE[it.tone] ?? TONE.info;
                    return (
                      <li key={j} className={`tone-${it.tone}`}>
                        <Icon size={16} aria-hidden="true" />
                        <span>
                          <span className="sr-only">{word}: </span>
                          <strong>{it.label}</strong>
                          <span className="num-wrap">{it.value}</span>
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </details>
            )}
          </div>
        </li>
      ))}
    </ol>
    </>
  );
}
