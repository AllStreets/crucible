import { loadDataset, stageRows } from "../../lib/dataset";
import { VesselPanel } from "../../components/VesselPanel";

export const metadata = { title: "Explorer | CRUCIBLE" };

export default function Explorer() {
  const data = loadDataset();
  const stages = stageRows(data);

  // Grouped by the stage each agent reached. Derived, so a new stage or a new
  // agent appears here without anyone editing this page.
  const byStage = new Map<number, typeof stages>();
  for (const r of stages) {
    const list = byStage.get(r.stage) ?? [];
    list.push(r);
    byStage.set(r.stage, list);
  }
  const tiers = [...byStage.entries()].sort((a, b) => b[0] - a[0]);

  return (
    <div className="sheet page">
      <p className="label">Explorer</p>
      <h1>The vessel, and what survived each stage</h1>
      <p className="lede">
        Every agent that entered the instrument, drawn at the height of the
        stage it reached. The narrowing is the finding: getting an agent to the
        starting line is the hard part, and nobody has published how hard.
      </p>

      <VesselPanel specimens={stages} />

      <section className="tiers">
        {tiers.map(([stage, rows]) => (
          <div key={stage} className="tier panel">
            <header>
              <span className="label">{rows[0].label}</span>
              <span className="mono n">{rows.length}</span>
            </header>
            <ul>
              {rows.map((r) => (
                <li key={r.slug}>
                  <code>{r.slug}</code>
                  {r.failure && <span className="fail">{r.failure}</span>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1rem; max-width: 20ch; }
        .lede { color: var(--ink-soft); font-size: var(--t-lead); max-width: 58ch;
                margin-bottom: 2rem; }
        .tiers { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                 gap: 1rem; margin-top: 2rem; }
        .tier { padding: 1.1rem; }
        .tier header { display: flex; justify-content: space-between;
                       align-items: baseline; padding-bottom: 0.6rem;
                       border-bottom: var(--hair) solid var(--rule); }
        .tier .n { font-size: var(--t-h3); color: var(--ink); }
        .tier ul { list-style: none; margin: 0.8rem 0 0; padding: 0;
                   display: flex; flex-direction: column; gap: 0.5rem; }
        .tier li { display: flex; flex-direction: column; gap: 0.15rem;
                   font-size: var(--t-small); }
        .tier .fail { font-family: var(--font-mono); font-size: var(--t-micro);
                      color: var(--signal-warn); }
      `}</style>
    </div>
  );
}
