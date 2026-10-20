export interface AttritionStage { key: string; label: string; count: number; tone: string }

/** Attrition as connected bands, drawn to scale.
 *
 *  Each stage is a bar whose width is its count over the first stage; the
 *  band between two bars is the loss, and it is drawn rather than implied
 *  because the loss is the finding. Pure SVG from props: nothing is placed by
 *  hand and nothing needs recasting when the counts change. */
export function Attrition({ stages }: { stages: AttritionStage[] }) {
  const W = 720, rowH = 44, gap = 26, left = 230, right = 60;
  const total = Math.max(1, stages[0]?.count ?? 1);
  const H = stages.length * (rowH + gap) - gap + 8;
  const bw = (c: number) => Math.max(2, (W - left - right) * (c / total));
  return (
    <div className="scroll-x">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="attrition by stage" style={{ minWidth: 520 }}>
        <defs>
          {stages.map((s) => (
            <linearGradient key={s.key} id={`g-${s.key}`} x1="0" x2="1">
              <stop offset="0" stopColor={s.tone} stopOpacity="0.55" />
              <stop offset="1" stopColor={s.tone} stopOpacity="1" />
            </linearGradient>
          ))}
        </defs>
        {stages.map((s, i) => {
          const y = i * (rowH + gap) + 4;
          const w = bw(s.count);
          const next = stages[i + 1];
          return (
            <g key={s.key}>
              <text x={left - 14} y={y + rowH / 2 + 4} textAnchor="end" fill="var(--ink-soft)"
                    style={{ font: "500 11px var(--font-mono)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                {s.label}
              </text>
              <rect x={left} y={y} width={W - left - right} height={rowH} fill="var(--ground-raised)" stroke="var(--rule)" />
              <rect x={left} y={y} width={w} height={rowH} fill={`url(#g-${s.key})`} />
              <text x={left + w + 10} y={y + rowH / 2 + 5} fill="var(--ink)"
                    style={{ font: "500 16px var(--font-mono)", fontVariantNumeric: "tabular-nums" }}>
                {s.count}
              </text>
              {next && (
                <polygon
                  points={`${left},${y + rowH} ${left + w},${y + rowH} ${left + bw(next.count)},${y + rowH + gap} ${left},${y + rowH + gap}`}
                  fill={s.tone} opacity="0.13" />
              )}
              {next && s.count - next.count > 0 && (
                <text x={left + w + 10} y={y + rowH + gap / 2 + 4} fill="var(--warn)"
                      style={{ font: "11px var(--font-mono)" }}>
                  {`-${s.count - next.count}`}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
