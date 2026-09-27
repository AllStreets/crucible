import { loadDataset, stageRows } from "../../lib/dataset";
import { VesselPanel } from "../../components/VesselPanel";
import { GraphPanel } from "../../components/GraphPanel";
import { buildGraph, legendFor, stageLegend } from "../../lib/graph";

export const metadata = { title: "Explorer | Crucible" };

export default function Explorer() {
  const data = loadDataset();
  const stages = stageRows(data);
  const graph = buildGraph(data);
  const byStage = new Map<number, typeof stages>();
  for (const r of stages) byStage.set(r.stage, [...(byStage.get(r.stage) ?? []), r]);
  const tiers = [...byStage.entries()].sort((a, b) => b[0] - a[0]);
  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Explorer</span><span className="label">{stages.length} agents</span></div>
        <h1>The vessel, and the graph.</h1>
        <p className="lede">Two views of the same rows. The vessel places every agent at the height of the stage it survived to, so the narrowing is the finding. The graph draws every run between a pair as an edge, so hubs emerge from the data rather than being chosen.</p>
      </div>
      <figure className="fig"><VesselPanel specimens={stages} /><figcaption><b>Figure 1</b><span>One specimen per agent, at the height of the stage it reached.</span></figcaption></figure>
      <figure className="fig"><GraphPanel nodes={graph.nodes} links={graph.links} stageKey={stageLegend(graph.nodes)} edgeKey={legendFor(graph.links)} /><figcaption><b>Figure 2</b><span>Every agent, and every run between a pair. Node size is degree.</span></figcaption></figure>
      <div className="spec">
        {tiers.map(([stage, rows]) => (
          <div key={stage} className="contents">
            <span className="k">{rows[0].label}</span>
            <div className="v"><p className="mono" style={{ fontSize: "var(--t-small)" }}>{rows.map((r) => <a key={r.slug} href={`/agents/${r.slug}/`} style={{ marginRight: "1.2rem", textDecoration: "none" }}>{r.slug}{r.failure ? <span style={{ color: "var(--warn)" }}> · {r.failure}</span> : ""}</a>)}</p></div>
          </div>
        ))}
      </div>
      <style>{`.contents { display: contents; } .vessel-panel, .graph-panel { border: 0; padding: 0; background: transparent; }`}</style>
    </div>
  );
}
