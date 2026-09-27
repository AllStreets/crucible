import { scenarioInfo, type PairRow } from "../../lib/dataset";

/** The recorder trace: every run as a tick in its scenario's lane, in the
 *  order it happened. Colour is what the run established. The newest tick
 *  pulses. This is the figure that grows as the research runs; nothing in it
 *  is placed by hand. */
const COLOR: Record<string, string> = {
  done: "var(--earned)", fail: "var(--accent)", artifact: "var(--artifact)",
  blocked: "var(--refused)", lost: "var(--stop)", queued: "var(--refused)", running: "var(--warn)",
};

export function StripChart({ runs }: { runs: PairRow[] }) {
  const ordered = [...runs].sort((a, b) => a.id - b.id);
  const lanes = [...new Set(ordered.map((r) => r.scenario))].sort();
  const laneH = 34, left = 190, right = 56, tickW = 4, gap = 3;
  const W = Math.max(720, left + right + ordered.length * (tickW + gap) + 20);
  const H = lanes.length * laneH + 26;
  const x = (i: number) => left + i * (tickW + gap);
  const last = ordered[ordered.length - 1];
  const first = ordered[0];

  return (
    <div className="scroll-x">
      <svg className="strip" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="every run, by scenario, in order" style={{ minWidth: 720 }}>
        {lanes.map((lane, li) => {
          const y = li * laneH;
          const mine = ordered.map((r, i) => [r, i] as const).filter(([r]) => r.scenario === lane);
          const earned = mine.filter(([r]) => r.status === "done").length;
          return (
            <g key={lane}>
              <line x1={left} x2={W - right} y1={y + laneH / 2} y2={y + laneH / 2} stroke="var(--rule)" />
              <text x={left - 14} y={y + laneH / 2 + 5} textAnchor="end" fill="var(--ink)"
                    style={{ font: "italic 15px var(--font-display)" }}>{scenarioInfo(lane).title}</text>
              <text x={W - right + 10} y={y + laneH / 2 + 4} fill="var(--ink-faint)"
                    style={{ font: "11px var(--font-mono)" }}>{earned}/{mine.length}</text>
              {mine.map(([r, i]) => {
                const key = r.status === "done" && r.outcome === "fail" ? "fail" : r.status;
                const h = r.status === "done" ? 20 : 12;
                return (
                  <rect key={r.id} className={`tick${r.id === last?.id ? " latest" : ""}`}
                        x={x(i)} y={y + laneH / 2 - h / 2} width={tickW} height={h}
                        fill={COLOR[key] ?? "var(--refused)"} style={{ color: COLOR[key] ?? "var(--refused)" }}>
                    <title>{`${scenarioInfo(lane).title}: ${r.status}${r.outcome ? ", " + r.outcome : ""}${r.strength ? ", " + r.strength : ""}`}</title>
                  </rect>
                );
              })}
            </g>
          );
        })}
        {first && last && (
          <>
            <text x={left} y={H - 4} fill="var(--ink-faint)" style={{ font: "10px var(--font-mono)" }}>{first.at.slice(0, 16).replace("T", " ")}</text>
            <text x={W - right} y={H - 4} textAnchor="end" fill="var(--ink-faint)" style={{ font: "10px var(--font-mono)" }}>{last.at.slice(0, 16).replace("T", " ")}</text>
          </>
        )}
      </svg>
    </div>
  );
}
