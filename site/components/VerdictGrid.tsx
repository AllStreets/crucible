import Link from "next/link";
import { pairKey, runsByScenario, scenarioInfo, type Dataset } from "../lib/dataset";

const TONE: Record<string, string> = { done: "ok", artifact: "artifact", blocked: "inert", lost: "stop", running: "active", queued: "inert" };

/** One card per scenario that has been run: the question it asks, the most
 *  recent run's status and outcome, how strong that is, and the run's own
 *  note as evidence. Scenarios with no runs are absent, not stubbed. */
export function VerdictGrid({ data }: { data: Dataset }) {
  const by = runsByScenario(data);
  const names = Object.keys(by).sort();
  return (
    <div className="grid-2">
      {names.map((name) => {
        const runs = by[name];
        const cur = runs[runs.length - 1];
        const earned = runs.filter((r) => r.status === "done").length;
        const info = scenarioInfo(name);
        const note = (cur.blocked_reason ?? "").split(". ").slice(0, 2).join(". ");
        return (
          <article key={name} className="panel scenario" id={name}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h3>{info.title}</h3>
              <span className="label">{info.objective}</span>
            </div>
            <p className="q">{info.question}</p>
            <div className="row">
              <span className={`pill ${TONE[cur.status] ?? "inert"}`}>{cur.status}</span>
              <code className="mono" style={{ color: "var(--ink)" }}>{cur.outcome ?? "not reached"}</code>
              {cur.strength && <span className={`pill ${cur.strength === "strong" ? "hot" : "warn"}`}>{cur.strength} evidence</span>}
            </div>
            {note && <p className="evidence">{note}{note.endsWith(".") ? "" : "."}</p>}
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="label">{runs.length} runs, {earned} earned</span>
              <Link href={`/pairs/${pairKey(cur.slug_a, cur.slug_b)}/#${name}`} className="label" style={{ color: "var(--accent)" }}>
                every run
              </Link>
            </div>
          </article>
        );
      })}
    </div>
  );
}
