import { eur, month, TODAY } from "./format";

export type PlanGoal = {
  title: string;
  horizon: "now" | "long";
  target: number;
  saved: number;
  deadline: string;
  eta: string | null;
  on_course: boolean;
  reached: boolean;
};

const W = 358;
const PAD = 16;
const time = (iso: string) => new Date(iso + "T00:00:00").getTime();

/** One static route: Today → stopovers → destination. Position = arrival date (ETA, else planned date). */
export function Route({ goals }: { goals: PlanGoal[] }) {
  const at = (g: PlanGoal) => g.eta ?? g.deadline;
  const start = time(TODAY);
  const end = Math.max(start + 1, ...goals.map((g) => time(at(g))));
  const x = (iso: string) => PAD + ((time(iso) - start) / (end - start)) * (W - 2 * PAD);
  const sorted = [...goals].sort((a, b) => time(at(a)) - time(at(b)));
  const summary = sorted.map((g) => `${g.title}, ${g.horizon === "now" ? "stopover" : "destination"}, arrives ${month(at(g))}`).join("; ");

  return (
    <svg className="route" viewBox={`0 0 ${W} 112`} role="img" aria-label={`Flight plan from today: ${summary || "no goals yet"}`}>
      <line x1={PAD} y1={56} x2={W - PAD} y2={56} stroke="var(--border)" strokeWidth={2} strokeDasharray="2 6" strokeLinecap="round" />
      {sorted.length > 0 && (
        <line x1={PAD} y1={56} x2={x(at(sorted[sorted.length - 1]))} y2={56} stroke="var(--brand-cyan)" strokeWidth={3} strokeLinecap="round" />
      )}
      <circle cx={PAD} cy={56} r={5} fill="var(--navy)" />
      <text x={PAD} y={84} textAnchor="start">Today</text>
      {sorted.map((g, i) => {
        const cx = x(at(g));
        const up = i % 2 === 0;
        const anchor = cx > W - 70 ? "end" : cx < 70 ? "start" : "middle";
        const dest = g.horizon === "long";
        return (
          <g key={g.title + i}>
            {dest ? (
              <circle cx={cx} cy={56} r={9} fill="var(--surface)" stroke="var(--navy)" strokeWidth={3} />
            ) : (
              <circle cx={cx} cy={56} r={6} fill="var(--surface)" stroke="var(--action-blue)" strokeWidth={2.5} />
            )}
            {!g.on_course && !g.reached && <circle cx={cx} cy={56} r={2.5} fill="var(--warning)" />}
            <text className="label" x={cx} y={up ? 30 : 88} textAnchor={anchor}>{g.title}</text>
            <text x={cx} y={up ? 16 : 102} textAnchor={anchor}>{month(at(g))}</text>
          </g>
        );
      })}
    </svg>
  );
}

export function GoalRows({ goals }: { goals: PlanGoal[] }) {
  return (
    <div className="list">
      {goals.map((g, i) => (
        <div className="goal-row" key={g.title + i}>
          <div className="goal-row-head">
            <strong>{g.title}</strong>
            <span className="meta">{g.horizon === "now" ? "Stopover" : "Destination"}</span>
          </div>
          <div className="progress" aria-hidden="true"><span style={{ width: `${Math.min(100, (g.saved / g.target) * 100)}%` }} /></div>
          <div className="goal-row-head small">
            <span className="num">{eur(g.saved, true)} of {eur(g.target, true)}</span>
            <Status g={g} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Status({ g }: { g: PlanGoal }) {
  if (g.reached) return <span className="badge ok">Arrived</span>;
  if (!g.eta) return <span className="badge off">No arrival date yet</span>;
  return g.on_course
    ? <span className="small">ETA {month(g.eta)} · <span className="badge ok">On course</span></span>
    : <span className="small">ETA {month(g.eta)} · <span className="badge off">Off course</span></span>;
}
