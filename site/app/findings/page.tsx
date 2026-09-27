import { failuresByClass, loadDataset, agentRows } from "../../lib/dataset";
import { FAILURE_LABELS } from "../../lib/failures";

export const metadata = { title: "Findings | Crucible" };
const HARNESS = new Set(["unsupported_language", "workspace_root_not_installable", "python_version_unsupported", "no_build_recipe", "ambiguous_manifest", "unknown"]);

export default function Findings() {
  const data = loadDataset();
  const failures = Object.entries(failuresByClass(data)).sort((a, b) => b[1] - a[1]);
  const rows = agentRows(data);
  const harness = failures.filter(([c]) => HARNESS.has(c)).reduce((n, [, v]) => n + v, 0);
  const repo = failures.reduce((n, [, v]) => n + v, 0) - harness;
  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Findings</span><span className="label">{failures.length} classes recorded</span></div>
        <h1>Every recorded failure, and whose it is.</h1>
        <p className="lede">Tallies of failure rows, not a partition of the agents: a candidate that fails to build contributes a build row and no check row. Each class carries an attribution, because a rate driven by limits of this harness describes the harness, and a reader cannot tell that from a class name alone.</p>
        <div className="figures" style={{ marginTop: "1.5rem" }}>
          <div><span className="figure warn" style={{ color: "var(--warn)" }}>{harness}</span><span className="cap">failures that are limits of this harness</span></div>
          <div><span className="figure" style={{ color: "var(--stop)" }}>{repo}</span><span className="cap">failures that are properties of the repository</span></div>
        </div>
      </div>
      <div className="spec">
        {failures.map(([cls, n]) => (
          <div key={cls} className="contents">
            <span className="k"><span className="figure small">{n}</span></span>
            <div className="v stack" style={{ gap: "0.6rem", paddingBottom: "0.6rem" }}>
              <h3 style={{ fontStyle: "italic" }}>{FAILURE_LABELS[cls] ?? cls}</h3>
              <p className="note"><span className={`state ${HARNESS.has(cls) ? "warn" : "stop"}`}>{HARNESS.has(cls) ? "a limit of this harness" : "a property of the repository"}</span> <code style={{ color: "var(--ink-faint)", marginLeft: "0.8rem" }}>{cls}</code></p>
              <ul className="agents">
                {rows.filter((r) => r.failureClass === cls).map((r) => (
                  <li key={r.slug}><a href={`/agents/${r.slug}/`}><code>{r.slug}</code></a><a href={r.repoUrl} rel="noreferrer" className="mono faint">{r.repoUrl.replace("https://github.com/", "")}</a><code className="faint">{r.commitSha.slice(0, 10)}</code></li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
      <style>{`
        .contents { display: contents; } .figure.small { font-size: 2.4rem; line-height: 1; }
        .faint { color: var(--ink-faint); font-size: var(--t-micro); }
        .agents { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.35rem; }
        .agents li { display: flex; gap: 1rem; align-items: baseline; flex-wrap: wrap; font-size: var(--t-small); }
        .agents a { text-decoration: none; }
      `}</style>
    </div>
  );
}
