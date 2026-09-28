import { loadManifest, loadPapers } from "../../lib/dataset";

export const metadata = { title: "Papers | CRUCIBLE" };

export default function Papers() {
  const papers = loadPapers();
  const m = loadManifest();

  // Two kinds of paper, and they are read differently. The standing ones
  // restate the whole record every time they are generated, so they are what a
  // reader cites and there will only ever be a handful. The pass reports are a
  // log: one per experiment, each written from the rows its own pass wrote,
  // and their number is the number of experiments that have run. Listing them
  // together buried the standing papers under a growing pile of run reports.
  const standing = papers.filter((p) => !p.slug.startsWith("pass-"));
  const runs = papers
    .filter((p) => p.slug.startsWith("pass-"))
    .sort((a, b) => b.slug.localeCompare(a.slug));

  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow">
          <span className="label">Papers</span>
          <span className="label">{papers.length} verified</span>
        </div>
        <h1>Generated from records. Verified against them.</h1>
        <p className="lede">
          Each paper is rendered from a typed template whose every numeric slot is a query, then
          read back by a verifier that refuses to emit the document if any numeral in it is
          absent from the record. The PDF is typeset from that verified text and nothing else.
          No model writes these, so they cannot drift from the data.
        </p>
      </div>

      {papers.length === 0 ? (
        <p className="note">
          No paper currently verifies against the record. Generation refuses to emit a document
          the data cannot support.
        </p>
      ) : (
        <>
          <section className="block">
            <h2>Standing results.</h2>
            <p className="deck">
              Regenerated from the whole record on every pass, so each is always current and
              none of them accumulates. These are the ones to cite.
            </p>
            <div className="spec papers">
              {standing.map((p, i) => (
                <div key={p.slug} className="contents">
                  <span className="k"><span className="figure small">{String(i + 1).padStart(2, "0")}</span></span>
                  <div className="v paper">
                    <h3>{p.title}</h3>
                    <div className="meta">
                      <span className="state done">verified</span>
                      {p.pages && <span className="mono faint">{p.pages} pages</span>}
                      <span className="mono faint">{p.word_count} words</span>
                      <span className="mono faint">regenerated {p.generated_at.slice(0, 10)}</span>
                      {p.pdf_sha256 && <span className="mono faint">pdf sha256 {p.pdf_sha256.slice(0, 12)}</span>}
                    </div>
                    <p className="abstract"><em>Abstract.</em> {p.abstract}</p>
                    <div className="actions">
                      {p.pdf && <a className="btn primary" href={`/papers/${p.pdf}`} download>Download the PDF</a>}
                      {p.pdf && <a className="btn" href={`/papers/${p.pdf}`} target="_blank" rel="noreferrer">Read in the browser</a>}
                      <a className="mono faint" href={`/papers/${p.filename}`} style={{ alignSelf: "center" }}>source markdown</a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {runs.length > 0 && (
            <section className="block">
              <h2>One report per experiment.</h2>
              <p className="deck">
                A pass is an experiment: parameters fixed before it began, a window in which it
                ran, and rows that exist because it ran. Each report is written from those rows
                and no others, so it stays true as the record grows past it. Newest first.
              </p>
              <div className="runs">
                {runs.map((p) => (
                  <article key={p.slug} className="run">
                    <div className="run-head">
                      <h3>{p.title}</h3>
                      <span className="state done">verified</span>
                    </div>
                    <p className="abstract">{p.abstract}</p>
                    <div className="run-foot">
                      <span className="mono faint">
                        {p.pages ? `${p.pages} pages` : ""}{p.pages ? " · " : ""}{p.word_count} words
                      </span>
                      <span className="links">
                        {p.pdf && <a href={`/papers/${p.pdf}`} download>PDF</a>}
                        {p.pdf && <a href={`/papers/${p.pdf}`} target="_blank" rel="noreferrer">read</a>}
                        <a href={`/papers/${p.filename}`}>markdown</a>
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <p className="note">
        Generated against the dataset published {m.generated_at.slice(0, 10)}, engine{" "}
        <code>{m.engine_commit.slice(0, 12)}</code>.
      </p>

      <style>{`
        .contents { display: contents; }
        .figure.small { font-size: 2.4rem; line-height: 1; }
        .faint { color: var(--ink-faint); font-size: var(--t-small); }
        .paper { display: flex; flex-direction: column; gap: 0.9rem; padding-bottom: 1.6rem; }
        .paper h3 { font-style: italic; max-width: 26ch; font-size: var(--t-h2); }
        .meta { display: flex; gap: 1.2rem; align-items: baseline; flex-wrap: wrap; }
        .abstract { max-width: 70ch; color: var(--ink-soft); }
        .abstract em { color: var(--ink); }
        .actions { display: flex; gap: 0.8rem; flex-wrap: wrap; padding-top: 0.3rem; }
        .papers .k { padding-top: 1.2rem; }

        .runs { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 0; }
        .run { display: flex; flex-direction: column; gap: 0.7rem; padding: 1.2rem 1.6rem 1.4rem 0;
          border-top: var(--hair) solid var(--rule); min-width: 0; }
        .run-head { display: flex; align-items: baseline; gap: 1rem; justify-content: space-between; }
        .run-head h3 { font-family: var(--font-display); font-style: italic; font-size: var(--t-h3);
          white-space: nowrap; }
        .run .abstract { font-size: var(--t-small); max-width: 52ch; }
        .run-foot { display: flex; align-items: baseline; justify-content: space-between;
          gap: 1rem; margin-top: auto; padding-top: 0.4rem; }
        .run-foot .links { display: flex; gap: 1rem; font-size: var(--t-small); }
      `}</style>
    </div>
  );
}
