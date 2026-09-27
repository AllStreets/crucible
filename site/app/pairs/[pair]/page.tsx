import Link from "next/link";
import { loadDataset, pairSummaries, scenarioInfo } from "../../../lib/dataset";

export function generateStaticParams() {
  return pairSummaries(loadDataset()).map((p) => ({ pair: p.key }));
}
export const dynamicParams = false;

const TONE: Record<string, string> = { done: "ok", artifact: "artifact", blocked: "inert", lost: "stop", running: "active", queued: "inert" };

export default async function PairPage({ params }: { params: Promise<{ pair: string }> }) {
  const { pair } = await params;
  const data = loadDataset();
  const p = pairSummaries(data).find((x) => x.key === pair);
  if (!p) return null;
  const byScenario = new Map<string, typeof p.runs>();
  for (const r of p.runs) byScenario.set(r.scenario, [...(byScenario.get(r.scenario) ?? []), r]);

  return (
    <div className="sheet page stack">
      <div>
        <div className="crumbs"><Link href="/pairs/">pairs</Link><span>/</span><span>{p.key}</span></div>
        <h1><code>{p.a}</code> against <code>{p.b}</code></h1>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
          <span className="pill ok">{p.earned} earned</span><span className="pill hot">{p.strong} strong</span>
          <span className="pill artifact">{p.artifacts} artifact</span><span className="pill inert">{p.blocked} refused</span>
          <Link href={`/agents/${p.a}/`} className="label">{p.a}</Link><Link href={`/agents/${p.b}/`} className="label">{p.b}</Link>
        </div>
      </div>
      {[...byScenario.keys()].sort().map((name) => (
        <section key={name} id={name} className="panel">
          <div className="panel-head"><span className="title">{scenarioInfo(name).title}</span><span className="label">{byScenario.get(name)!.length} runs, newest last</span></div>
          <p className="note" style={{ padding: "0.7rem 1rem 0" }}>{scenarioInfo(name).question}</p>
          <div className="stack" style={{ padding: "1rem", gap: "0.8rem" }}>
            {byScenario.get(name)!.map((r) => (
              <article key={r.id} className="panel" style={{ padding: "0.9rem 1rem" }}>
                <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap" }}>
                  <span className={`pill ${TONE[r.status] ?? "inert"}`}>{r.status}</span>
                  <code style={{ color: "var(--ink)" }}>{r.outcome ?? "not reached"}</code>
                  {r.strength && <span className={`pill ${r.strength === "strong" ? "hot" : "warn"}`}>{r.strength} evidence</span>}
                  <code className="mono" style={{ marginLeft: "auto", fontSize: "var(--t-micro)", color: "var(--ink-faint)" }}>{r.sandbox_run_id?.slice(-24)}</code>
                </div>
                <dl className="kv" style={{ marginTop: "0.7rem" }}>
                  <dt>model</dt><dd><code>{r.model}</code></dd>
                  <dt>recorded</dt><dd><code>{r.at.slice(0, 19).replace("T", " ")}</code></dd>
                  <dt>{r.status === "done" ? "evidence" : "why not a verdict"}</dt><dd>{r.blocked_reason ?? "no note"}</dd>
                </dl>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
