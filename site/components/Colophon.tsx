import { loadManifest } from "../lib/dataset";

/** Provenance on every page, not on an about page nobody opens. */
export function Colophon() {
  const m = loadManifest();
  return (
    <footer className="colophon">
      <div className="inner sheet">
        <div className="cols">
          <div><span className="label">Engine commit</span><code>{m.engine_commit.slice(0, 12)}</code></div>
          <div><span className="label">Dataset sha256</span><code>{m.dataset_sha256.slice(0, 16)}</code></div>
          <div><span className="label">Generated</span><code>{m.generated_at.slice(0, 19).replace("T", " ")} UTC</code></div>
        </div>
        <p className="note">
          Every figure here is a count of rows in the published dataset. None is
          asserted, and the site has no connection to the running engine, so it
          cannot display a number that was not published.
        </p>
      </div>
      <style>{`
        .colophon { border-top: var(--hair) solid var(--rule); margin-top: 3rem;
                    background: var(--ground-raised); }
        .colophon .inner { padding-top: 2.2rem; padding-bottom: 3rem; }
        .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
                gap: 1rem 2rem; }
        .cols div { display: flex; flex-direction: column; gap: 0.3rem; }
        .cols code { font-size: var(--t-small); color: var(--ink-soft); }
        .note { font-size: var(--t-small); color: var(--ink-soft);
                border-left: 2px solid var(--accent-cool); padding-left: 0.9rem;
                margin-top: 1.5rem; }
      `}</style>
    </footer>
  );
}
