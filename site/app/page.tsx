import Link from "next/link";
import { agentRows, failuresByClass, loadDataset, viability } from "../lib/dataset";
import { FAILURE_LABELS } from "../lib/failures";

export default function Home() {
  const data = loadDataset();
  const v = viability(data);
  const rows = agentRows(data);
  const failures = Object.entries(failuresByClass(data))
    .sort((a, b) => b[1] - a[1]);

  const pct = v.rate === null ? null : (v.rate * 100).toFixed(1);

  return (
    <div className="home sheet">
      <section className="finding">
        <p className="label">The measurement</p>

        <p className="claim">
          Of the agents harvested, this many were built into a container whose
          environment starts in a clean sandbox.
        </p>

        <p className="figure">
          <span className="mono">{v.checked}</span>
          <span className="of">of</span>
          <span className="mono">{v.harvested}</span>
          {pct !== null && <span className="pct mono">{pct}%</span>}
        </p>

        <p className="counterclaim">
          It does not measure whether the agent runs. The probe starts the
          interpreter, prints one line and exits. The repositories measured
          here share no entrypoint, and with no network and no credentials an
          invocation would measure this harness rather than the agent, so no
          figure on this page is evidence that an agent ran.
        </p>
      </section>

      <section className="stages">
        <h2>What each stage measured</h2>
        <div className="scroll-x">
          <table className="rows">
            <thead>
              <tr><th>Agent</th><th>Build</th><th>Environment check</th><th className="num">Probe</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.slug}>
                  <td><code>{r.slug}</code></td>
                  <td>
                    {r.status === "built"
                      ? <span className="ok">built</span>
                      : <span className="no">{FAILURE_LABELS[r.failureClass ?? ""] ?? r.failureClass}</span>}
                  </td>
                  <td>{r.checkPassed ? <span className="ok">passed</span> : <span className="dash">not reached</span>}</td>
                  <td className="num">
                    {r.checkDurationMs === null ? <span className="dash">&ndash;</span> : `${r.checkDurationMs} ms`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="failures">
        <h2>Why the rest did not</h2>
        <p className="note">
          These are tallies of recorded failure rows and are not a partition of
          the agents above. A candidate that fails to build contributes a build
          row and no check row, so these counts neither sum to the harvested
          count nor are bounded by it.
        </p>
        <ul>
          {failures.map(([cls, n]) => (
            <li key={cls}>
              <span className="mono count">{n}</span>
              <span className="cls">{FAILURE_LABELS[cls] ?? cls}</span>
              <code className="raw">{cls}</code>
            </li>
          ))}
        </ul>
        <p className="more"><Link href="/findings">Every failure class, with what it means</Link></p>
      </section>

      <section className="defects">
        <h2>What running it cost</h2>
        <p>
          The engine was reviewed eight times before it was ever run against a
          live Docker daemon. Running it found defects that reading had not, and
          the log records each one rather than the clean result alone.
        </p>
        <p className="more"><Link href="/log">The research log, including retractions</Link></p>
      </section>

      <style>{`
        
        section { padding: 3rem 0; border-bottom: var(--rule-hair) solid var(--rule); }
        section:last-of-type { border-bottom: 0; }

        .finding { padding-top: 3.5rem; }
        .claim {
          font-family: var(--font-display);
          font-size: var(--t-lead);
          margin-top: 0.9rem;
          color: var(--ink);
        }
        .figure {
          display: flex;
          align-items: baseline;
          gap: 0.75rem;
          margin: 1.75rem 0;
          font-size: var(--t-figure);
          font-family: var(--font-mono);
          font-variant-numeric: tabular-nums;
          line-height: 1;
        }
        .figure .of {
          font-family: var(--font-display);
          font-size: var(--t-h3);
          color: var(--ink-soft);
          font-style: italic;
        }
        .figure .pct {
          font-size: var(--t-h2);
          color: var(--accent);
          margin-left: 0.5rem;
        }
        /* Deliberately the same size and weight as the claim above the figure.
           The caveat is the page's argument, not a footnote to it. */
        .counterclaim {
          font-family: var(--font-display);
          font-size: var(--t-lead);
          color: var(--ink);
          border-left: 2px solid var(--signal-warn);
          padding-left: 1.1rem;
        }

        h2 { margin-bottom: 1.25rem; }
        .note, .more { font-size: var(--t-small); color: var(--ink-soft); margin-top: 1rem; }
        .ok { color: var(--accent); }
        .no { color: var(--signal-warn); }
        .dash { color: var(--ink-soft); }

        .failures ul { list-style: none; padding: 0; margin: 1.5rem 0 0; }
        .failures li {
          display: flex;
          align-items: baseline;
          gap: 1rem;
          padding: 0.7rem 0;
          border-bottom: var(--rule-hair) solid var(--rule);
        }
        .failures .count {
          font-size: var(--t-h3);
          min-width: 2.5ch;
          text-align: right;
          color: var(--signal-warn);
        }
        .failures .cls { flex: 1; }
        .failures .raw { font-size: var(--t-micro); color: var(--ink-soft); }
      `}</style>
    </div>
  );
}
