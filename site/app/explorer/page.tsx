import { lattice, loadDataset, repoNames, stageRows } from "../../lib/dataset";
import { ArenaLattice } from "../../components/viz/ArenaLattice";
import { Attrition } from "../../components/viz/Attrition";

export const metadata = { title: "Explorer | Crucible" };

export default function Explorer() {
  const data = loadDataset();
  const stages = stageRows(data);
  const grid = lattice(data);
  const names = repoNames(data);
  const byStage = new Map<number, typeof stages>();
  for (const r of stages) byStage.set(r.stage, [...(byStage.get(r.stage) ?? []), r]);
  const tiers = [...byStage.entries()].sort((a, b) => b[0] - a[0]);
  const ordered = grid.agents.length * (grid.agents.length - 1) * grid.scenarios.length;

  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Explorer</span><span className="label">{stages.length} agents</span></div>
        <h1>Who attacked, who defended, under what.</h1>
        <p className="lede">
          A pair is not symmetric. One agent writes into the shared workspace and the other
          reads it, and a pair that holds one way round has not been shown to hold the other.
          A flat matrix collapses those two facts into one cell; here they are separate axes,
          so a gap reads as a direction nobody has run rather than as an attack that failed.
        </p>
      </div>

      <figure className="fig">
        <ArenaLattice data={grid} names={names} />
        <figcaption>
          <b>Figure 1</b>
          <span>
            {grid.cells.length} of {ordered} ordered pairings run, over {grid.scenarios.length} scenarios
            and {grid.agents.length} agents that can be invoked. {grid.missing} directions have never been run.
          </span>
        </figcaption>
      </figure>

      <section className="block">
        <h2>Getting to the starting line.</h2>
        <p className="deck">
          Most agents never reach the solid above. The band between two bars is what was lost
          there, and it is the finding that took the longest to earn.
        </p>
        <figure className="fig">
          <Attrition stages={[
            { key: "harvested", label: "harvested", count: stages.length, tone: "#3E6E8E" },
            { key: "built", label: "built", count: stages.filter((r) => r.stage >= 1).length, tone: "#34A48F" },
            { key: "checked", label: "env starts", count: stages.filter((r) => r.stage >= 2).length, tone: "#34A48F" },
            { key: "invocable", label: "invocable", count: grid.agents.length, tone: "#C9922A" },
          ]} />
          <figcaption><b>Figure 2</b><span>Each bar is a count of rows; the width is its share of the agents harvested.</span></figcaption>
        </figure>
      </section>

      <div className="spec">
        {tiers.map(([stage, rows]) => (
          <div key={stage} className="contents">
            <span className="k">{rows[0].label}</span>
            <div className="v"><p className="mono" style={{ fontSize: "var(--t-small)" }}>{rows.map((r) => <a key={r.slug} href={`/agents/${r.slug}/`} style={{ marginRight: "1.2rem", textDecoration: "none" }}>{r.slug}{r.failure ? <span style={{ color: "var(--warn)" }}> · {r.failure}</span> : ""}</a>)}</p></div>
          </div>
        ))}
      </div>
      <style>{`.contents { display: contents; }`}</style>
    </div>
  );
}
