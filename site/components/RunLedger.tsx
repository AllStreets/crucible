import Link from "next/link";
import { pairKey, scenarioInfo, type PairRow } from "../lib/dataset";

const TONE: Record<string, string> = {
  done: "ok", artifact: "artifact", blocked: "inert", lost: "stop", running: "active", queued: "inert",
};

function when(at: string) {
  return at ? `${at.slice(5, 10)} ${at.slice(11, 16)}` : "";
}

/** The most recent runs, newest first. Reads like a tape: what ran, what it
 *  established, and whether that counts. */
export function RunLedger({ runs, limit }: { runs: PairRow[]; limit?: number }) {
  const rows = [...runs].sort((a, b) => b.id - a.id).slice(0, limit ?? runs.length);
  return (
    <div className="ledger">
      {rows.map((r) => (
        <Link key={r.id} href={`/pairs/${pairKey(r.slug_a, r.slug_b)}/#${r.scenario}`} className="ledger-row">
          <span className="when">{when(r.at)}</span>
          <span className="what">
            <span>{scenarioInfo(r.scenario).title}</span>
            <code>{r.slug_a} against {r.slug_b}</code>
          </span>
          <span className="row" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            {r.strength && <span className={`pill ${r.strength === "strong" ? "hot" : "warn"}`}>{r.strength}</span>}
            <span className={`pill ${TONE[r.status] ?? "inert"}`}>{r.status}</span>
            <code className="mono" style={{ color: "var(--ink-soft)", fontSize: "var(--t-micro)" }}>{r.outcome ?? "not reached"}</code>
          </span>
        </Link>
      ))}
      <style>{`.ledger-row { text-decoration: none; color: inherit; }`}</style>
    </div>
  );
}
