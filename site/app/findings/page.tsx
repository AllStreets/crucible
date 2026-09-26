import { failuresByClass, loadDataset, agentRows } from "../../lib/dataset";
import { FAILURE_LABELS } from "../../lib/failures";

export const metadata = { title: "Findings | CRUCIBLE" };

export default function Findings() {
  const data = loadDataset();
  const failures = Object.entries(failuresByClass(data)).sort((a, b) => b[1] - a[1]);
  const rows = agentRows(data);

  return (
    <div className="sheet page">
      <p className="label">Findings</p>
      <h1>Every recorded failure, and what it means</h1>

      <p className="note">
        Tallies of recorded failure rows, not a partition of the agents. A
        candidate that fails to build contributes a build row and no check row,
        so these counts neither sum to the harvested count nor are bounded by
        it. Each class links to the agents that carry it.
      </p>

      {failures.map(([cls, n]) => (
        <section key={cls} className="cls">
          <header>
            <span className="mono n">{n}</span>
            <div>
              <h2>{FAILURE_LABELS[cls] ?? cls}</h2>
              <code className="raw">{cls}</code>
            </div>
          </header>
          <ul>
            {rows.filter((r) => r.failureClass === cls).map((r) => (
              <li key={r.slug}>
                <code>{r.slug}</code>
                <a href={r.repoUrl} rel="noreferrer">{r.repoUrl.replace("https://github.com/", "")}</a>
                <code className="sha">{r.commitSha.slice(0, 12)}</code>
              </li>
            ))}
          </ul>
        </section>
      ))}

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1.25rem; max-width: 22ch; }
        .note { font-size: var(--t-small); color: var(--ink-soft); margin-bottom: 2.5rem; }
        .cls { padding: 1.75rem 0; border-top: var(--rule-hair) solid var(--rule); }
        .cls header { display: flex; gap: 1.25rem; align-items: baseline; }
        .cls .n {
          font-size: var(--t-h2);
          color: var(--signal-warn);
          min-width: 2.5ch;
          text-align: right;
        }
        .cls h2 { font-size: var(--t-h3); }
        .cls .raw { font-size: var(--t-micro); color: var(--ink-soft); }
        .cls ul { list-style: none; padding: 0; margin: 1rem 0 0 calc(2.5ch + 1.25rem); }
        .cls li {
          display: flex;
          gap: 1rem;
          align-items: baseline;
          flex-wrap: wrap;
          font-size: var(--t-small);
          padding: 0.35rem 0;
        }
        .cls .sha { color: var(--ink-soft); font-size: var(--t-micro); }
      `}</style>
    </div>
  );
}
