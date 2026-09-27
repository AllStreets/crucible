import { loadManifest, loadPapers } from "../../lib/dataset";

export const metadata = { title: "Papers | CRUCIBLE" };

export default function Papers() {
  const papers = loadPapers(); const m = loadManifest();
  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Papers</span><span className="label">{papers.length} verified</span></div>
        <h1>Generated from records. Verified against them.</h1>
        <p className="lede">Each paper is rendered from a typed template whose every numeric slot is a query. The generator then reads its own output back and refuses to emit the document if any numeral in it is absent from the record. No model writes these, and they are regenerated on every research pass, so they cannot drift from the data.</p>
      </div>
      {papers.length === 0 ? (
        <p className="note">No paper currently verifies against the record. Generation refuses to emit a document the data cannot support.</p>
      ) : (
        <div className="spec papers">
          {papers.map((p, i) => (
            <div key={p.slug} className="contents">
              <span className="k"><span className="figure small">{String(i + 1).padStart(2, "0")}</span></span>
              <div className="v paper">
                <h2>{p.title}</h2>
                <div className="meta">
                  <span className="state done">verified</span>
                  <span className="mono faint">{p.word_count} words</span>
                  <span className="mono faint">regenerated {p.generated_at.slice(0, 10)}</span>
                  <span className="mono faint">sha256 {p.sha256.slice(0, 12)}</span>
                </div>
                <p className="abstract"><em>Abstract.</em> {p.abstract}</p>
                <div className="actions">
                  <a className="btn primary" href={`/papers/${p.filename}`} download>Download the paper</a>
                  <a className="btn" href={`/papers/${p.filename}`} target="_blank" rel="noreferrer">Read in the browser</a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="note">Generated against the dataset published {m.generated_at.slice(0, 10)}, engine <code>{m.engine_commit.slice(0, 12)}</code>.</p>
      <style>{`
        .contents { display: contents; }
        .figure.small { font-size: 2.4rem; line-height: 1; }
        .faint { color: var(--ink-faint); font-size: var(--t-micro); }
        .paper { display: flex; flex-direction: column; gap: 0.9rem; padding-bottom: 1.6rem; }
        .paper h2 { font-style: italic; max-width: 26ch; }
        .meta { display: flex; gap: 1.2rem; align-items: baseline; flex-wrap: wrap; }
        .abstract { max-width: 70ch; color: var(--ink-soft); }
        .abstract em { color: var(--ink); }
        .actions { display: flex; gap: 0.8rem; flex-wrap: wrap; padding-top: 0.3rem; }
        .papers .k { padding-top: 1.2rem; }
      `}</style>
    </div>
  );
}
