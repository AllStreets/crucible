/** Failure causes as a ranked bar chart, with attribution encoded in colour.
 *
 *  The attribution split is the load-bearing part: a rate driven by harness
 *  limits says something about the harness, and a reader cannot tell the two
 *  apart from a class name alone.
 */
export interface Cause {
  cls: string;
  label: string;
  count: number;
  harness: boolean;
  agents: string[];
}

export function Distribution({ causes }: { causes: Cause[] }) {
  const max = Math.max(1, ...causes.map((c) => c.count));
  return (
    <div className="dist">
      <div className="key">
        <span className="state warn">harness limit</span>
        <span className="state stop">repository</span>
      </div>
      {causes.map((c) => (
        <article key={c.cls}>
          <div className="row">
            <span className="mono n">{c.count}</span>
            <div className="body">
              <div className="top">
                <span className="name">{c.label}</span>
                <code className="cls">{c.cls}</code>
              </div>
              <div className="track">
                <div
                  className={`bar ${c.harness ? "harness" : "repo"}`}
                  style={{ width: `${(c.count / max) * 100}%` }}
                />
              </div>
              <p className="who">{c.agents.join("  ")}</p>
            </div>
          </div>
        </article>
      ))}
      <style>{`
        .dist { display: flex; flex-direction: column; gap: 1.2rem; }
        .key { display: flex; gap: 0.6rem; }
        .row { display: flex; gap: 1rem; align-items: flex-start; }
        .row .n { font-size: var(--t-h2); color: var(--ink); min-width: 2ch;
                  text-align: right; line-height: 1.1; }
        .body { flex: 1; min-width: 0; }
        .top { display: flex; justify-content: space-between; gap: 1rem;
               align-items: baseline; flex-wrap: wrap; }
        .name { font-size: var(--t-small); }
        .cls { font-size: var(--t-micro); color: var(--ink-faint); }
        .track { height: 6px; background: var(--ground-raised); margin-top: 0.45rem;
                 border: var(--hair) solid var(--rule); border-radius: 2px;
                 overflow: hidden; }
        .bar { height: 100%; }
        .bar.harness { background: linear-gradient(90deg, #7A5A16, var(--signal-warn)); }
        .bar.repo    { background: linear-gradient(90deg, #7A2A24, var(--signal-stop)); }
        .who { font-family: var(--font-mono); font-size: var(--t-micro);
               color: var(--ink-faint); margin-top: 0.4rem; }
      `}</style>
    </div>
  );
}
