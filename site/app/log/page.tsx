import { LOG } from "../../lib/log";

export const metadata = { title: "Log | CRUCIBLE" };

export default function LogPage() {
  return (
    <div className="sheet page">
      <p className="label">Research log</p>
      <h1>What changed, and what was withdrawn</h1>

      <p className="note">
        Retractions stay here rather than being deleted. A withdrawn claim that
        vanishes leaves a reader unable to tell whether it was ever made.
      </p>

      <ol className="entries">
        {LOG.map((e, i) => (
          <li key={i} className={e.kind}>
            <div className="meta">
              <code>{e.date}</code>
              {e.kind === "retraction" && <span className="tag">Retraction</span>}
            </div>
            <div className="body">
              <h2>{e.title}</h2>
              {e.withdrawn && (
                <p className="withdrawn"><s>{e.withdrawn}</s></p>
              )}
              <p>{e.body}</p>
            </div>
          </li>
        ))}
      </ol>

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1rem; max-width: 22ch; }
        .note { font-size: var(--t-small); color: var(--ink-soft); margin-bottom: 2.5rem; }
        .entries { list-style: none; padding: 0; margin: 0; }
        .entries li {
          display: grid;
          grid-template-columns: 10rem 1fr;
          gap: 1.5rem;
          padding: 1.75rem 0;
          border-top: var(--rule-hair) solid var(--rule);
        }
        .entries li.retraction { border-top: 2px solid var(--signal-stop); }
        .meta { display: flex; flex-direction: column; gap: 0.4rem; }
        .meta code { font-size: var(--t-small); color: var(--ink-soft); }
        .tag {
          font-family: var(--font-mono); font-size: var(--t-micro);
          letter-spacing: 0.11em; text-transform: uppercase;
          color: var(--signal-stop);
        }
        .entries h2 { font-size: var(--t-h3); margin-bottom: 0.6rem; }
        .withdrawn { color: var(--ink-soft); font-style: italic; margin-bottom: 0.6rem; }
        @media (max-width: 700px) {
          .entries li { grid-template-columns: 1fr; gap: 0.6rem; }
          .meta { flex-direction: row; gap: 1rem; }
        }
      `}</style>
    </div>
  );
}
