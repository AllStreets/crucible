import { scenarioInfo, type PairRow } from "../../lib/dataset";

/** The recorder trace: every run as a tick in its scenario's lane, in the
 *  order it happened. Colour is what the run established. The newest tick
 *  pulses. This is the figure that grows as the research runs; nothing in it
 *  is placed by hand.
 *
 *  The lane names, the counts and the dates are HTML, and only the ticks are
 *  drawn. They used to be text inside the drawing, which meant they were
 *  subject to its scale: the drawing widens with every run, the column it sits
 *  in does not, and at three hundred runs the whole figure was being squeezed
 *  to two fifths of its size, taking the type down with it. Every word here is
 *  now set in the page's own sizes and stays there however long the trace
 *  gets; the ticks scroll instead, which is the part that is supposed to grow.
 */
const COLOR: Record<string, string> = {
  done: "var(--earned)", fail: "var(--accent)", artifact: "var(--artifact)",
  blocked: "var(--refused)", lost: "var(--stop)", queued: "var(--refused)", running: "var(--warn)",
};

const LANE_H = 30;

export function StripChart({ runs }: { runs: PairRow[] }) {
  const ordered = [...runs].sort((a, b) => a.id - b.id);
  const lanes = [...new Set(ordered.map((r) => r.scenario))].sort();
  const tickW = 4, gap = 3;
  const W = Math.max(600, ordered.length * (tickW + gap) + 8);
  const H = lanes.length * LANE_H;
  const last = ordered[ordered.length - 1];
  const first = ordered[0];

  const perLane = lanes.map((lane) => {
    const mine = ordered.map((r, i) => [r, i] as const).filter(([r]) => r.scenario === lane);
    return { lane, mine, earned: mine.filter(([r]) => r.status === "done").length };
  });

  return (
    <div className="trace">
      <div className="lanes" aria-hidden="true">
        {perLane.map(({ lane }) => (
          <span key={lane} className="lane-name">{scenarioInfo(lane).title}</span>
        ))}
      </div>

      <div className="scroll-x ticks">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          role="img"
          aria-label={`every run, by scenario, in order: ${ordered.length} runs`}
        >
          {perLane.map(({ lane, mine }, li) => {
            const y = li * LANE_H;
            return (
              <g key={lane}>
                <line x1={0} x2={W} y1={y + LANE_H / 2} y2={y + LANE_H / 2} stroke="var(--rule)" />
                {mine.map(([r, i]) => {
                  const key = r.status === "done" && r.outcome === "fail" ? "fail" : r.status;
                  const h = r.status === "done" ? 18 : 11;
                  return (
                    <rect
                      key={r.id}
                      className={`tick${r.id === last?.id ? " latest" : ""}`}
                      x={i * (tickW + gap)} y={y + LANE_H / 2 - h / 2}
                      width={tickW} height={h}
                      fill={COLOR[key] ?? "var(--refused)"}
                      style={{ color: COLOR[key] ?? "var(--refused)" }}
                    >
                      <title>{`${scenarioInfo(lane).title}: ${r.status}${r.outcome ? ", " + r.outcome : ""}${r.strength ? ", " + r.strength : ""}`}</title>
                    </rect>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="tallies" aria-hidden="true">
        {perLane.map(({ lane, mine, earned }) => (
          <span key={lane} className="tally">{earned}<span className="of">/{mine.length}</span></span>
        ))}
      </div>

      {first && last && (
        <p className="span">
          <span>{first.at.slice(0, 16).replace("T", " ")}</span>
          <span>{last.at.slice(0, 16).replace("T", " ")}</span>
        </p>
      )}

      <style>{`
        .trace { display: grid; grid-template-columns: auto minmax(0, 1fr) auto;
          column-gap: 1rem; align-items: start; }
        .lanes, .tallies { display: grid; }
        .lanes .lane-name, .tallies .tally { height: ${LANE_H}px; display: flex; align-items: center; }
        .lane-name { font-family: var(--font-display); font-style: italic; font-size: var(--t-lead);
          color: var(--ink); white-space: nowrap; justify-content: flex-end; }
        .tally { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-soft);
          font-variant-numeric: tabular-nums; }
        .tally .of { color: var(--ink-faint); }
        /* This drawing is meant to be wider than its column and to scroll,
           so it must opt out of the rule that keeps every other figure inside
           one. Constrained, it scaled down instead, taking its own height with
           it and tearing the ticks away from the lane names beside them. */
        .trace .ticks svg { display: block; max-width: none; }
        .span { grid-column: 2; display: flex; justify-content: space-between;
          font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-faint);
          margin-top: 0.5rem; max-width: none; }
        @media (max-width: 720px) {
          .trace { grid-template-columns: minmax(0, 1fr); row-gap: 0.4rem; }
          .lanes, .tallies { grid-auto-flow: column; justify-content: start; gap: 1.1rem; }
          .lanes .lane-name, .tallies .tally { height: auto; }
          .lane-name { font-size: var(--t-small); justify-content: flex-start; }
          .span { grid-column: 1; }
        }
      `}</style>
    </div>
  );
}
