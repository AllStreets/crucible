import { loadManifest } from "../lib/dataset";

/** Provenance on every page, not on an about page nobody opens.
 *
 *  The engine commit and the dataset digest are what let a reader check that
 *  the numbers above came from a specific state of a specific codebase, and
 *  that the file describing them was not edited afterwards. */
export function Colophon() {
  const m = loadManifest();
  return (
    <footer className="colophon">
      <div>
        <span className="label">Engine commit</span>
        <code>{m.engine_commit.slice(0, 12)}</code>
      </div>
      <div>
        <span className="label">Dataset sha256</span>
        <code>{m.dataset_sha256.slice(0, 16)}</code>
      </div>
      <div>
        <span className="label">Generated</span>
        <code>{m.generated_at.slice(0, 19).replace("T", " ")} UTC</code>
      </div>
      <p className="note">
        Every figure on this site is a count of rows in the published dataset.
        None is asserted, and the site has no connection to the running engine,
        so it cannot display a number that was not published.
      </p>

      <style>{`
        .colophon {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
          gap: 1.1rem 2rem;
          padding: 2.5rem clamp(1.25rem, 5vw, 3rem) 3.5rem;
          max-width: 1060px;
          margin-left: auto;
          margin-right: auto;
          border-top: var(--rule-hair) solid var(--rule);
          margin-top: 3.5rem;
          position: relative;
          z-index: 1;
          background: var(--ground);
        }
        .colophon div { display: flex; flex-direction: column; gap: 0.3rem; }
        .colophon code { font-size: var(--t-small); color: var(--ink-soft); }
        .colophon .note {
          grid-column: 1 / -1;
          font-size: var(--t-small);
          color: var(--ink-soft);
          max-width: var(--measure);
          border-left: 2px solid var(--accent);
          padding-left: 0.9rem;
        }
      `}</style>
    </footer>
  );
}
