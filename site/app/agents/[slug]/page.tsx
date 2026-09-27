import Link from "next/link";
import { agentDetail, loadDataset, pairKey, scenarioInfo } from "../../../lib/dataset";
import { FAILURE_LABELS } from "../../../lib/failures";

export function generateStaticParams() {
  return loadDataset().candidates.map((c) => ({ slug: c.slug }));
}
export const dynamicParams = false;

const OUT: Record<string, string> = { acted: "ok", ran_no_effect: "warn", failed: "stop" };
const TONE: Record<string, string> = { done: "ok", artifact: "artifact", blocked: "inert", lost: "stop", running: "active", queued: "inert" };

export default async function AgentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const d = agentDetail(loadDataset(), slug);
  if (!d) return null;
  const b = d.build, c = d.check;
  // The recipe's own default. Anything else was asked for by a seed line.
  const DEFAULT_BASE = "python:3.11-slim";
  return (
    <div className="sheet page stack">
      <div>
        <div className="crumbs"><Link href="/agents/">agents</Link><span>/</span><span>{slug}</span></div>
        <h1><code>{slug}</code></h1>
        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap" }}>
          <span className={`pill ${d.stage.stage >= 4 ? "hot" : d.stage.stage === 3 ? "active" : d.stage.stage >= 1 ? "ok" : "inert"}`}>{d.stage.label}</span>
          <a href={d.candidate.repo_url} rel="noreferrer" className="label">{d.candidate.repo_url.replace("https://github.com/", "")}</a>
        </div>
      </div>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head"><span className="title">Build</span>{b && <span className={`pill ${b.status === "built" ? "ok" : "warn"}`}>{b.status}</span>}</div>
          <dl className="kv panel-body">
            <dt>commit</dt><dd><code>{d.candidate.commit_sha}</code></dd>
            {b?.failure_class && <><dt>cause</dt><dd>{FAILURE_LABELS[b.failure_class] ?? b.failure_class} <code style={{ color: "var(--ink-faint)" }}>{b.failure_class}</code></dd></>}
            {b?.image_digest && <><dt>image</dt><dd><code>{b.image_digest}</code></dd></>}
            {b?.recipe_sha && <><dt>recipe</dt><dd><code>{b.recipe_sha}</code></dd></>}
            {b?.log_ref && <><dt>build log</dt><dd><code>{b.log_ref}</code></dd></>}
            {b?.base_image && b.base_image !== DEFAULT_BASE && <><dt>base image</dt><dd><code>{b.base_image}</code> <span className="note">not the recipe default, declared by the seed because this agent requires a newer interpreter than the recipe provides</span></dd></>}
            {b?.extras && <><dt>extras</dt><dd><code>{b.extras}</code> <span className="note">installed with the package, declared beside the invocation</span></dd></>}
            {b?.pins && <><dt>versions forced</dt><dd><code>{b.pins}</code> <span className="note">installed after this agent resolved its own dependencies, because the release it chose cannot execute on the machine that built it. This row is not comparable with one built without the override, which is why it is recorded here.</span></dd></>}
            {d.builds.length > 1 && <><dt>earlier attempts</dt><dd>{d.builds.slice(0, -1).map((x) => <span key={x.id} className="attempt"><code>{x.status}</code>{x.failure_class ? <span className="note"> {FAILURE_LABELS[x.failure_class] ?? x.failure_class}</span> : null}</span>)}<span className="note">Kept because a build that failed and a build that later succeeded are two observations, and the reason each row exists is the record.</span></dd></>}
          </dl>
        </section>
        <section className="panel">
          <div className="panel-head"><span className="title">Environment check</span>{c ? <span className={`pill ${c.status === "passed" ? "ok" : "stop"}`}>{c.status}</span> : <span className="pill inert">not reached</span>}</div>
          <dl className="kv panel-body">
            {c ? <>
              <dt>probe</dt><dd>{c.duration_ms} ms</dd>
              <dt>model pinned</dt><dd><code>{c.model ?? "none"}</code></dd>
              <dt>base url</dt><dd><code>{c.base_url ?? "none"}</code></dd>
              <dt>measures</dt><dd>that the interpreter starts in a clean sandbox. It does not invoke the agent.</dd>
            </> : <><dt>why</dt><dd>No image to start: the build did not succeed.</dd></>}
          </dl>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head"><span className="title">Entrypoint</span><span className="label">{d.entrypoints.length} recorded</span></div>
        {d.entrypoints.length === 0 ? (
          <p className="note panel-body">No entrypoint. An agent absent from the arena with no stated reason would be indistinguishable from one nobody got round to; the reasons live in the repository under entrypoints/NOT-INVOCABLE.md.</p>
        ) : d.entrypoints.slice(-1).map((e) => (
          <div key={e.id} className="panel-body stack">
            <pre className="mono" style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "var(--t-micro)", color: "var(--ink-soft)", background: "var(--ground-raised)", padding: "0.8rem", borderRadius: 3, border: "var(--hair) solid var(--rule)" }}>{e.command.join(" ")}</pre>
            <dl className="kv">
              <dt>authored by</dt><dd><code>{e.authored_by}</code></dd>
              <dt>env required</dt><dd><code>{e.env_required.join(", ")}</code></dd>
              <dt>notes</dt><dd>{e.notes}</dd>
            </dl>
          </div>
        ))}
      </section>

      {d.solos.length > 0 && (
        <section className="panel">
          <div className="panel-head"><span className="title">Solo gate, every attempt</span><span className="label">the failures are why the entrypoint is trusted</span></div>
          <div className="scroll-x"><table>
            <thead><tr><th>Outcome</th><th>Model</th><th className="num">Duration</th><th>Recorded</th></tr></thead>
            <tbody>{d.solos.map((s) => (
              <tr key={s.id}><td><span className={`pill ${OUT[s.outcome] ?? "inert"}`}>{s.outcome}</span></td>
                <td><code>{s.model}</code></td><td className="num">{s.duration_ms} ms</td><td><code style={{ color: "var(--ink-faint)" }}>{s.at.slice(0, 19).replace("T", " ")}</code></td></tr>
            ))}</tbody>
          </table></div>
        </section>
      )}

      {d.pairs.length > 0 && (
        <section className="panel">
          <div className="panel-head"><span className="title">In the arena</span><span className="label">{d.pairs.length} runs</span></div>
          <div className="scroll-x"><table>
            <thead><tr><th>Scenario</th><th>Against</th><th>Status</th><th>Outcome</th><th>Evidence</th></tr></thead>
            <tbody>{[...d.pairs].sort((a, b) => b.id - a.id).map((p) => (
              <tr key={p.id}>
                <td><Link href={`/pairs/${pairKey(p.slug_a, p.slug_b)}/#${p.scenario}`}>{scenarioInfo(p.scenario).title}</Link></td>
                <td><code>{p.slug_a === slug ? p.slug_b : p.slug_a}</code></td>
                <td><span className={`pill ${TONE[p.status] ?? "inert"}`}>{p.status}</span></td>
                <td><code>{p.outcome ?? "not reached"}</code></td>
                <td>{p.strength ? <span className={`pill ${p.strength === "strong" ? "hot" : "warn"}`}>{p.strength}</span> : <span className="label">none</span>}</td>
              </tr>))}</tbody>
          </table></div>
        </section>
      )}
    </div>
  );
}
