import { loadManifest } from "../lib/dataset";

/** Provenance on every page. The engine commit and the dataset digest are what
 *  let a reader check that the numbers above came from a specific state of a
 *  specific codebase, and that the file describing them was not edited after. */
export function Colophon() {
  const m = loadManifest();
  return (
    <footer className="colophon">
      <div className="inner sheet">
        <div className="spec">
          <span className="k">Engine</span><span className="v"><code>{m.engine_commit}</code></span>
          <span className="k">Dataset</span><span className="v"><code>sha256 {m.dataset_sha256}</code></span>
          <span className="k">Generated</span><span className="v"><code>{m.generated_at.slice(0, 19).replace("T", " ")} UTC</code></span>
          <span className="k">Also</span>
          <span className="v secondary">
            {[["/methodology/", "Method"], ["/threat-model/", "Threat model"], ["/data/", "Data"], ["/about/", "About"], ["/submit/", "Submit"]].map(([h, l]) => (
              <a key={h} href={h}>{l}</a>
            ))}
          </span>
        </div>
        <p className="note">
          Every figure on this site is a count of rows in the published dataset. None is asserted,
          and the site has no connection to the running engine, so it cannot display a number
          that was not published.
        </p>
      </div>
      <style>{`
        .colophon { border-top: var(--hair) solid var(--rule-strong); margin-top: 3rem; }
        .colophon .inner { padding-top: 1.5rem; padding-bottom: 3.5rem; }
        .colophon code { color: var(--ink-soft); font-size: var(--t-small); }
        .secondary { display: flex; gap: 1.4rem; flex-wrap: wrap; }
        .secondary a { font-size: var(--t-small); color: var(--ink-soft); text-decoration: none; }
        .secondary a:hover { color: var(--ink); }
        .colophon .note { margin-top: 1.5rem; max-width: 62ch; }
      `}</style>
    </footer>
  );
}
