import { loadManifest, loadPapers } from "../../lib/dataset";

export const metadata = { title: "Papers | CRUCIBLE" };

export default function Papers() {
  const papers = loadPapers();
  const m = loadManifest();

  return (
    <div className="sheet page">
      <p className="label">Papers</p>
      <h1>Generated from records, verified against them</h1>
      <p className="lede">
        Each paper is rendered from a typed template whose every numeric slot is
        a query. The generator then reads its own output back and refuses to
        emit the document if any numeral in it is absent from the record. No
        model writes these.
      </p>

      {papers.length === 0 ? (
        <div className="panel empty">
          <span className="pill inert">none published</span>
          <p>
            No paper currently verifies against the record. Generation refuses
            to emit a document the data cannot support, rather than publishing
            an empty template.
          </p>
        </div>
      ) : (
        <ol className="papers">
          {papers.map((p, i) => (
            <li key={p.slug} className="panel">
              <div className="meta">
                <span className="idx mono">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <h2>{p.title}</h2>
                  <div className="facts">
                    <span className="pill ok">verified</span>
                    <span className="mono">{p.word_count} words</span>
                    <span className="mono">{p.generated_at.slice(0, 10)}</span>
                  </div>
                </div>
              </div>

              <div className="abstract">
                <span className="label">Abstract</span>
                <p>{p.abstract}</p>
              </div>

              <div className="actions">
                <a className="btn primary" href={`/papers/${p.filename}`} download>
                  Download the full paper
                </a>
                <a className="btn" href={`/papers/${p.filename}`} target="_blank" rel="noreferrer">
                  Read in browser
                </a>
                <code className="sha">sha256 {p.sha256.slice(0, 16)}</code>
              </div>
            </li>
          ))}
        </ol>
      )}

      <p className="foot">
        Generated against the dataset published {m.generated_at.slice(0, 10)},
        engine <code>{m.engine_commit.slice(0, 12)}</code>.
      </p>

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1rem; max-width: 20ch; }
        .lede { color: var(--ink-soft); font-size: var(--t-lead); max-width: 58ch;
                margin-bottom: 2.5rem; }

        .papers { list-style: none; margin: 0; padding: 0;
                  display: flex; flex-direction: column; gap: 1.25rem; }
        .papers li { padding: 1.5rem; display: flex; flex-direction: column; gap: 1.1rem; }
        .meta { display: flex; gap: 1.1rem; align-items: flex-start; }
        .idx { font-size: var(--t-h2); color: var(--rule-bright); line-height: 1; }
        .meta h2 { font-size: var(--t-h3); }
        .facts { display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap;
                 margin-top: 0.5rem; font-size: var(--t-micro); color: var(--ink-faint); }

        .abstract { border-left: 2px solid var(--accent-cool); padding-left: 1rem; }
        .abstract p { font-size: var(--t-small); color: var(--ink-soft);
                      margin-top: 0.4rem; max-width: 74ch; }

        .actions { display: flex; gap: 0.7rem; align-items: center; flex-wrap: wrap;
                   padding-top: 0.3rem; }
        .btn { display: inline-flex; align-items: center; gap: 0.45rem;
               font-family: var(--font-mono); font-size: var(--t-micro);
               letter-spacing: 0.1em; text-transform: uppercase; text-decoration: none;
               padding: 0.6rem 1rem; border-radius: 2px;
               border: var(--hair) solid var(--rule-bright); color: var(--ink-soft);
               transition: border-color 160ms, color 160ms, box-shadow 160ms; }
        .btn:hover { color: var(--ink); border-color: var(--accent); }
        .btn.primary { color: var(--ground); background: var(--accent);
                       border-color: var(--accent); font-weight: 600; }
        .btn.primary:hover { box-shadow: var(--glow-accent); color: var(--ground); }
        .sha { font-size: var(--t-micro); color: var(--ink-faint); margin-left: auto; }

        .empty { padding: 1.75rem; display: flex; flex-direction: column;
                 gap: 0.8rem; align-items: flex-start; }
        .empty p { font-size: var(--t-small); color: var(--ink-soft); }
        .foot { font-size: var(--t-micro); color: var(--ink-faint); margin-top: 2.5rem; }
      `}</style>
    </div>
  );
}
