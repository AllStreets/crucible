import { LOG, type LogEntry } from "../lib/log";

/** The research log as a rail. Retractions keep the withdrawn claim struck
 *  through rather than deleted, because a claim that vanishes leaves a reader
 *  unable to tell whether it was ever made. */
export function DefectTimeline({ entries, limit }: { entries?: LogEntry[]; limit?: number }) {
  const rows = (entries ?? LOG).slice(0, limit ?? undefined);
  return (
    <div className="timeline">
      {rows.map((e, i) => (
        <div key={i} className={`entry ${e.kind}`}>
          <div className="row" style={{ display: "flex", gap: "0.7rem", alignItems: "baseline", marginBottom: "0.2rem" }}>
            <code className="mono" style={{ fontSize: "var(--t-micro)", color: "var(--ink-faint)" }}>{e.date}</code>
            {e.kind === "retraction" && <span className="pill stop">retraction</span>}
          </div>
          <h3>{e.title}</h3>
          {e.withdrawn && <p style={{ fontStyle: "italic", marginBottom: "0.3rem" }}><s>{e.withdrawn}</s></p>}
          <p>{e.body}</p>
        </div>
      ))}
    </div>
  );
}
