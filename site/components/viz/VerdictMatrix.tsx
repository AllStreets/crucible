import Link from "next/link";
import { pairSummaries, repoNames, runsByScenario, scenarioInfo, type Dataset, type PairRow } from "../../lib/dataset";

/** Scenarios across, pairs down, the latest run in each cell. This is the
 *  figure the arena grows into: a new agent adds a row per pair it joins, a
 *  new scenario adds a column, and every cell is the newest row for that
 *  pair and scenario. Nothing is placed by hand.
 *
 *  Each cell is a mark rather than a sentence. The first version wrote the
 *  state and the strength into every cell, which at ten pairs meant the same
 *  two words forty times: the table said everything and showed nothing, and
 *  at a common desktop width the last column fell off the edge. A matrix is
 *  for reading down a column, so the two facts a cell carries are encoded in
 *  the two things the eye compares without reading, colour and fill, and the
 *  words are kept for the legend, the tooltip and the screen reader. */
const WORD: Record<string, string> = {
  done: "held", fail: "attack confirmed", artifact: "instrument artifact",
  blocked: "refused", lost: "lost", queued: "queued", running: "running",
};

function tone(r: PairRow): string {
  if (r.status === "done") return r.outcome === "fail" ? "fail" : "done";
  return r.status;
}

/** The mark. A bar for a verdict, filled when the victim engaged with the
 *  planted material and hollow when it did not; a hollow diamond when the
 *  instrument rather than the agents ended the run; a rule when the sandbox
 *  refused it before either agent started. */
function Mark({ r }: { r: PairRow | undefined }) {
  if (!r) return <span className="mark none" aria-hidden="true" />;
  const t = tone(r);
  const shape = t === "artifact" || t === "blocked" || t === "lost" ? t : "bar";
  const fill = r.strength === "weak" ? "hollow" : "solid";
  return <span className={`mark ${shape} ${t} ${fill}`} aria-hidden="true" />;
}

function label(r: PairRow | undefined): string {
  if (!r) return "not run";
  const w = WORD[tone(r)] ?? tone(r);
  return r.strength ? `${w}, ${r.strength} evidence` : w;
}

export function VerdictMatrix({ data }: { data: Dataset }) {
  const pairs = pairSummaries(data);
  const scenarios = Object.keys(runsByScenario(data)).sort();
  const names = repoNames(data);
  if (pairs.length === 0) return null;
  const latest = new Map<string, PairRow>();
  for (const p of data.pairs) {
    const key = `${[p.slug_a, p.slug_b].sort().join("--")}|${p.scenario}`;
    const cur = latest.get(key);
    if (!cur || p.id > cur.id) latest.set(key, p);
  }
  const short = (slug: string) => names[slug] ?? slug;

  return (
    <div className="matrix-wrap">
      <div className="scroll-x">
        <table className="matrix">
          <thead>
            <tr>
              <th scope="col">Pair</th>
              {scenarios.map((s) => <th key={s} scope="col" className="sc">{scenarioInfo(s).title}</th>)}
              <th scope="col" className="num">Earned</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map((p) => (
              <tr key={p.key}>
                <th scope="row">
                  <Link href={`/pairs/${p.key}/`}>
                    <span>{short(p.a)}</span> <span className="v">against</span> <span>{short(p.b)}</span>
                  </Link>
                </th>
                {scenarios.map((s) => {
                  const r = latest.get(`${p.key}|${s}`);
                  const text = label(r);
                  return (
                    <td key={s} className="cell">
                      {r
                        ? <Link href={`/pairs/${p.key}/#${s}`} title={`${scenarioInfo(s).title}: ${text}`}><Mark r={r} /><span className="vh">{text}</span></Link>
                        : <><Mark r={undefined} /><span className="vh">{text}</span></>}
                    </td>
                  );
                })}
                <td className="num tally">{p.earned}<span className="v">/{p.runs.length}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="key">
        <li><span className="mark bar done solid" aria-hidden="true" />held, the victim engaged</li>
        <li><span className="mark bar done hollow" aria-hidden="true" />held, weak evidence</li>
        <li><span className="mark bar fail solid" aria-hidden="true" />attack confirmed</li>
        <li><span className="mark artifact" aria-hidden="true" />instrument artifact</li>
        <li><span className="mark blocked" aria-hidden="true" />refused before the agents started</li>
        <li><span className="mark none" aria-hidden="true" />not run</li>
      </ul>

      <style>{`
        .matrix-wrap { display: flex; flex-direction: column; gap: 1.1rem; }
        /* A flex child will not shrink below its content, so the table inside
           widened the document instead of scrolling in its own box, and a
           phone rendered the whole page zoomed out to fit one column of it. */
        .matrix-wrap > * { min-width: 0; }
        .matrix { table-layout: auto; }
        .matrix th[scope="col"] { vertical-align: bottom; }
        .matrix th.sc { width: 7.5rem; white-space: normal; line-height: 1.25; padding-right: 0.75rem; }
        .matrix th[scope="row"] { font-family: var(--font-mono); font-size: var(--t-micro); font-weight: 400;
          letter-spacing: 0; text-transform: none; color: var(--ink); white-space: nowrap;
          border-bottom-color: var(--rule); padding-right: 1.5rem; }
        .matrix th[scope="row"] a { text-decoration: none; }
        .matrix th[scope="row"] a:hover span:not(.v) { color: var(--accent); }
        .matrix .v { color: var(--ink-faint); }
        .matrix td.cell { padding: 0.55rem 0.75rem 0.55rem 0; }
        .matrix td.cell a { display: inline-flex; text-decoration: none; padding: 0.25rem 0; }
        .matrix .tally { font-family: var(--font-mono); font-size: var(--t-micro); color: var(--ink-soft); }

        .mark { display: inline-block; }
        .mark.bar { width: 30px; height: 9px; border-radius: 1px; }
        .mark.bar.solid { background: currentColor; }
        .mark.bar.hollow { background: transparent; box-shadow: inset 0 0 0 1px currentColor; }
        .mark.done { color: var(--earned); }
        .mark.fail { color: var(--accent); box-shadow: 0 0 10px rgba(228,99,42,0.55); }
        .mark.artifact { width: 9px; height: 9px; transform: rotate(45deg); color: var(--artifact);
          box-shadow: inset 0 0 0 1px currentColor; margin-left: 10px; }
        .mark.blocked, .mark.lost { width: 30px; height: 1px; background: var(--ink-faint); transform: translateY(-4px); }
        .mark.none { width: 4px; height: 4px; border-radius: 50%; background: var(--rule-strong); margin-left: 13px; transform: translateY(-2px); }

        .key { list-style: none; margin: 0; padding: 0.9rem 0 0; border-top: var(--hair) solid var(--rule);
          display: flex; flex-wrap: wrap; gap: 0.6rem 1.6rem; font-size: var(--t-micro);
          font-family: var(--font-mono); color: var(--ink-soft); }
        .key li { display: flex; align-items: center; gap: 0.5rem; }
        .key .mark.artifact, .key .mark.none { margin-left: 0; }
        .key .mark.blocked { transform: none; }
      `}</style>
    </div>
  );
}
