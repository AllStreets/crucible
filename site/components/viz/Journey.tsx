import Link from "next/link";
import type { StageRow } from "../../lib/dataset";

const STAGES = ["harvested", "built", "env starts", "invocable", "arena"];
const TONE = ["var(--t1)", "var(--t2)", "var(--t2)", "var(--t3)", "var(--t4)"];

/** Small multiples: one row per agent, one cell per stage, lit as far as the
 *  agent got. The whole population reads at a glance, and a new agent is a
 *  new row. */
export function Journey({ rows }: { rows: StageRow[] }) {
  const sorted = [...rows].sort((a, b) => b.stage - a.stage || a.slug.localeCompare(b.slug));
  return (
    <div className="journey">
      <div className="jrow head"><span /> {STAGES.map((s) => <span key={s} className="label">{s}</span>)}</div>
      {sorted.map((r) => (
        <Link key={r.slug} href={`/agents/${r.slug}/`} className="jrow">
          <span className="who"><code>{r.slug}</code>{r.failure && <span className="why">{r.failure}</span>}</span>
          {STAGES.map((s, i) => (
            <span key={s} className={`cell ${i <= r.stage ? "lit" : ""}`} style={i <= r.stage ? { background: TONE[i], boxShadow: i === r.stage ? `0 0 10px ${TONE[i]}` : "none" } : undefined} />
          ))}
        </Link>
      ))}
      <style>{`
        .journey { display: flex; flex-direction: column; }
        .jrow { display: grid; grid-template-columns: minmax(10rem, 1.4fr) repeat(5, minmax(0, 1fr)); gap: 0.5rem; align-items: center;
                padding: 0.55rem 0; border-top: var(--hair) solid var(--rule); text-decoration: none; color: inherit; }
        .jrow.head { border-top: 0; padding-bottom: 0.3rem; }
        .jrow.head .label { font-size: 0.62rem; }
        .jrow:hover .who code { color: var(--accent); }
        .who { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
        .who code { font-size: var(--t-small); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .why { font-family: var(--font-mono); font-size: 0.62rem; color: var(--warn); }
        .cell { height: 8px; border-radius: 1px; background: var(--ground-raised); border: var(--hair) solid var(--rule); }
        .cell.lit { border-color: transparent; }
        @media (max-width: 720px) { .jrow { grid-template-columns: minmax(7rem, 1.6fr) repeat(5, minmax(0, 1fr)); } .jrow.head .label { font-size: 0.5rem; letter-spacing: 0.04em; } }
      `}</style>
    </div>
  );
}
