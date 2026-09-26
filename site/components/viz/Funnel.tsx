/** The attrition funnel, drawn to scale from the dataset.
 *
 *  This is the finding the project exists to report, so it is a figure rather
 *  than a sentence: each bar's width is its count over the harvested count, and
 *  the drop between bars is the thing worth looking at.
 */
export interface Stage {
  key: string;
  label: string;
  count: number;
  note: string;
  tone: "t1" | "t2" | "t3" | "t4";
}

export function Funnel({ stages, total }: { stages: Stage[]; total: number }) {
  return (
    <ol className="funnel">
      {stages.map((s, i) => {
        const pct = total === 0 ? 0 : (s.count / total) * 100;
        const lost = i === 0 ? 0 : stages[i - 1].count - s.count;
        return (
          <li key={s.key}>
            <div className="head">
              <span className="label">{s.label}</span>
              <span className="mono count">{s.count}</span>
            </div>
            <div className="track">
              <div className={`bar ${s.tone}`} style={{ width: `${pct}%` }} />
              {lost > 0 && (
                <div className="lost" style={{ width: `${(lost / total) * 100}%` }} />
              )}
            </div>
            <p className="note">{s.note}</p>
          </li>
        );
      })}
      <style>{`
        .funnel { list-style: none; margin: 0; padding: 0; display: flex;
                  flex-direction: column; gap: 1.1rem; }
        .head { display: flex; justify-content: space-between; align-items: baseline;
                margin-bottom: 0.4rem; }
        .head .count { font-size: var(--t-h3); color: var(--ink); }
        .track { display: flex; height: 8px; background: var(--ground-raised);
                 border: var(--hair) solid var(--rule); border-radius: 2px;
                 overflow: hidden; }
        .bar { height: 100%; transition: width 700ms cubic-bezier(.2,.7,.3,1); }
        .bar.t1 { background: linear-gradient(90deg, #2A4A5E, var(--t1)); }
        .bar.t2 { background: linear-gradient(90deg, #1E6B61, var(--t2));
                  box-shadow: var(--glow-cool); }
        .bar.t3 { background: linear-gradient(90deg, #8A6419, var(--t3)); }
        .bar.t4 { background: linear-gradient(90deg, #A8471D, var(--t4));
                  box-shadow: var(--glow-accent); }
        .lost { height: 100%;
                background-image: repeating-linear-gradient(135deg,
                  var(--rule) 0 4px, transparent 4px 8px); }
        .note { font-size: var(--t-micro); color: var(--ink-soft); margin-top: 0.45rem;
                max-width: 60ch; }
      `}</style>
    </ol>
  );
}
