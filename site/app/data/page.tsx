import { loadManifest, loadSchema } from "../../lib/dataset";

export const metadata = { title: "Data | CRUCIBLE" };

export default function DataPage() {
  const schema = loadSchema();
  const m = loadManifest();

  return (
    <div className="sheet page">
      <p className="label">Data</p>
      <h1>The dataset, its schema, and its exclusions</h1>

      <p className="lead">
        Every figure on this site is a count of rows in one file. It is
        published here in the form the engine wrote it.
      </p>

      <p className="dl">
        <a href="/data/dataset.json" download>dataset.json</a>
        <code>sha256 {m.dataset_sha256.slice(0, 24)}</code>
      </p>

      <h2>Schema</h2>
      {Object.entries(schema).map(([table, cols]) => (
        <section key={table} className="tbl">
          <h3><code>{table}</code> <span className="label">{m.counts[table]} rows</span></h3>
          <div className="scroll-x">
            <p className="cols">{cols.map((c) => <code key={c}>{c}</code>)}</p>
          </div>
        </section>
      ))}

      <h2>Exclusions a reader needs</h2>
      <ul>
        <li>
          Superseded rows are absent. A correction is a new row plus a
          supersedes row, and publishing both would double count.
        </li>
        <li>
          Counts are over the whole store rather than a single run, so a store
          built from more than one seed list reports their union.
        </li>
        <li>
          Failure classification is substring based and therefore approximate.
          Unmatched failures go to an unknown bucket rather than to the nearest
          plausible class.
        </li>
        <li>
          The unknown bucket also holds failures of the harness rather than of
          an agent: a build past its timeout, and the docker command failing to
          run at all. Both store their exception text, so they are separable by
          reading the rows.
        </li>
      </ul>

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1.25rem; max-width: 22ch; }
        .lead { font-family: var(--font-display); font-size: var(--t-lead); }
        .dl {
          display: flex; gap: 1.25rem; align-items: baseline; flex-wrap: wrap;
          margin: 1.75rem 0 2.5rem; padding: 1rem 0;
          border-top: var(--rule-hair) solid var(--ink);
          border-bottom: var(--rule-hair) solid var(--rule);
        }
        .dl code { color: var(--ink-soft); font-size: var(--t-micro); }
        h2 { margin: 2.5rem 0 1rem; font-size: var(--t-h3); }
        .tbl { padding: 0.9rem 0; border-bottom: var(--rule-hair) solid var(--rule); }
        .tbl h3 { font-size: var(--t-body); display: flex; gap: 0.9rem; align-items: baseline; }
        .cols { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.6rem; max-width: none; }
        .cols code {
          font-size: var(--t-micro); color: var(--ink-soft);
          border: var(--rule-hair) solid var(--rule); padding: 0.15rem 0.45rem;
        }
        ul { max-width: var(--measure); padding-left: 1.1rem; font-size: var(--t-small); }
        li { margin-bottom: 0.6rem; color: var(--ink-soft); }
      `}</style>
    </div>
  );
}
