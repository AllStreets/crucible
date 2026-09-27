import Link from "next/link";
import { loadDataset, pairSummaries, runsByScenario, scenarioInfo } from "../../lib/dataset";
import { RunLedger } from "../../components/RunLedger";

export const metadata = { title: "Pairs | CRUCIBLE" };

export default function Pairs() {
  const data = loadDataset();
  const pairs = pairSummaries(data);
  const by = runsByScenario(data);
  return (
    <div className="sheet page stack">
      <div><p className="label">Pairs</p><h1>Every pair, and every run between them</h1>
        <p className="lede">A pair is two agents sharing one workspace. Each run is one scenario against that pair, and every run is kept whatever it established.</p></div>
      <div className="grid-3">
        {pairs.map((p) => (
          <Link key={p.key} href={`/pairs/${p.key}/`} className="panel scenario" style={{ textDecoration: "none", color: "inherit" }}>
            <h3><code>{p.a}</code> <span className="label">against</span> <code>{p.b}</code></h3>
            <div className="row">
              <span className="pill ok">{p.earned} earned</span>
              <span className="pill hot">{p.strong} strong</span>
              <span className="pill artifact">{p.artifacts} artifact</span>
              <span className="pill inert">{p.blocked} refused</span>
            </div>
            <span className="label">{p.runs.length} runs</span>
          </Link>
        ))}
      </div>
      {Object.keys(by).sort().map((name) => (
        <section key={name} id={name} className="panel">
          <div className="panel-head"><span className="title">{scenarioInfo(name).title}</span><span className="label">{by[name].length} runs</span></div>
          <p className="note" style={{ padding: "0.7rem 1rem 0" }}>{scenarioInfo(name).question}</p>
          <RunLedger runs={by[name]} />
        </section>
      ))}
    </div>
  );
}
