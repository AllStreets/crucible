import Link from "next/link";
import { pairSummaries, runsByScenario, scenarioInfo, type Dataset, type PairRow } from "../../lib/dataset";

/** Scenarios across, pairs down, the latest run in each cell. This is the
 *  figure the arena grows into: a new agent adds a row per pair it joins, a
 *  new scenario adds a column, and every cell is the newest row for that
 *  pair and scenario. Nothing is placed by hand. */
const WORD: Record<string, string> = { done: "held", fail: "confirmed", artifact: "artifact", blocked: "refused", lost: "lost", queued: "queued", running: "running" };

export function VerdictMatrix({ data }: { data: Dataset }) {
  const pairs = pairSummaries(data);
  const scenarios = Object.keys(runsByScenario(data)).sort();
  if (pairs.length === 0) return null;
  const latest = new Map<string, PairRow>();
  for (const p of data.pairs) {
    const key = `${[p.slug_a, p.slug_b].sort().join("--")}|${p.scenario}`;
    const cur = latest.get(key);
    if (!cur || p.id > cur.id) latest.set(key, p);
  }
  return (
    <div className="scroll-x">
      <table className="matrix">
        <thead><tr><th>Pair</th>{scenarios.map((s) => <th key={s}>{scenarioInfo(s).title}</th>)}<th className="num">Earned</th></tr></thead>
        <tbody>
          {pairs.map((p) => (
            <tr key={p.key}>
              <td><Link href={`/pairs/${p.key}/`} style={{ textDecoration: "none" }}><code>{p.a}</code> <span className="faint">against</span> <code>{p.b}</code></Link></td>
              {scenarios.map((s) => {
                const r = latest.get(`${p.key}|${s}`);
                if (!r) return <td key={s}><span className="state inert">not run</span></td>;
                const tone = r.status === "done" ? (r.outcome === "fail" ? "fail" : "done") : r.status;
                return <td key={s}><Link href={`/pairs/${p.key}/#${s}`} style={{ textDecoration: "none" }}><span className={`state ${tone}`}>{WORD[tone] ?? tone}{r.strength ? `, ${r.strength}` : ""}</span></Link></td>;
              })}
              <td className="num">{p.earned}<span className="faint">/{p.runs.length}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      <style>{`.faint { color: var(--ink-faint); font-size: var(--t-micro); } .matrix td { white-space: nowrap; }`}</style>
    </div>
  );
}
