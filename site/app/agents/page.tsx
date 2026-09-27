import Link from "next/link";
import { agentRows, loadDataset, stageRows } from "../../lib/dataset";
import { FAILURE_LABELS } from "../../lib/failures";

export const metadata = { title: "Agents | CRUCIBLE" };

export default function Agents() {
  const data = loadDataset();
  const stages = new Map(stageRows(data).map((s) => [s.slug, s]));
  const rows = agentRows(data).sort((a, b) => (stages.get(b.slug)!.stage - stages.get(a.slug)!.stage) || a.slug.localeCompare(b.slug));
  return (
    <div className="sheet page stack">
      <div><p className="label">Agents</p><h1>One page per agent, every row it touched</h1>
        <p className="lede">Sorted by how far each got. Click through to see the build, the environment check, every solo attempt including the ones that did nothing, and every pair it entered.</p></div>
      <div className="panel scroll-x">
        <table>
          <thead><tr><th>Agent</th><th>Stage reached</th><th>Build</th><th>Repository</th></tr></thead>
          <tbody>
            {rows.map((r) => { const s = stages.get(r.slug)!; return (
              <tr key={r.slug}>
                <td><Link href={`/agents/${r.slug}/`}><code>{r.slug}</code></Link></td>
                <td><span className={`pill ${s.stage >= 4 ? "hot" : s.stage === 3 ? "active" : s.stage >= 1 ? "ok" : "inert"}`}>{s.label}</span></td>
                <td>{r.status === "built" ? <span className="pill ok">built</span> : <span style={{ color: "var(--signal-warn)", fontSize: "var(--t-small)" }}>{FAILURE_LABELS[r.failureClass ?? ""] ?? r.failureClass}</span>}</td>
                <td><a href={r.repoUrl} rel="noreferrer" style={{ fontSize: "var(--t-small)", color: "var(--ink-soft)" }}>{r.repoUrl.replace("https://github.com/", "")}</a></td>
              </tr>); })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
