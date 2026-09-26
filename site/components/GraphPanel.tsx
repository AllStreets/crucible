"use client";

import dynamic from "next/dynamic";
import type { GraphLink, GraphNode } from "../lib/graph";

const InteractionGraph = dynamic(
  () => import("./viz/InteractionGraph").then((m) => m.InteractionGraph),
  { ssr: false, loading: () => <div className="graph-skeleton" /> },
);

export function GraphPanel({ nodes, links, stageKey, edgeKey }: {
  nodes: GraphNode[];
  links: GraphLink[];
  stageKey: { color: string; label: string }[];
  edgeKey: { key: string; color: string; label: string }[];
}) {
  return (
    <figure className="graph-panel panel">
      <figcaption>
        <span className="label">The interaction graph</span>
        <span className="cap">
          Every agent, and every run between a pair. Node size is how many runs
          an agent appears in, so hubs emerge from the data rather than being
          chosen.
        </span>
      </figcaption>

      <InteractionGraph nodes={nodes} links={links} />

      <div className="keys">
        <div>
          <span className="label">Node colour &middot; stage reached</span>
          <ul>
            {stageKey.map((k) => (
              <li key={k.label}>
                <span className="dot" style={{ background: k.color, boxShadow: `0 0 8px ${k.color}` }} />
                {k.label}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <span className="label">Edge colour &middot; what the run established</span>
          <ul>
            {edgeKey.map((k) => (
              <li key={k.key}>
                <span className="bar" style={{ background: k.color }} />
                {k.label}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <style>{`
        .graph-panel { margin: 0; padding: 1rem 1rem 0.9rem; overflow: hidden; }
        .graph-panel figcaption { display: flex; flex-direction: column; gap: 0.25rem;
                                  margin-bottom: 0.5rem; }
        .graph-panel .cap { font-size: var(--t-micro); color: var(--ink-soft);
                            max-width: 62ch; }
        .graph-skeleton { height: clamp(380px, 48vh, 540px);
          background: radial-gradient(ellipse 50% 45% at 50% 50%,
            rgba(46,156,142,0.07), transparent 70%); }
        .keys { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 0.9rem 2rem; padding-top: 0.7rem; margin-top: 0.4rem;
                border-top: var(--hair) solid var(--rule); }
        .keys ul { list-style: none; margin: 0.4rem 0 0; padding: 0;
                   display: flex; flex-direction: column; gap: 0.3rem; }
        .keys li { display: flex; align-items: center; gap: 0.5rem;
                   font-family: var(--font-mono); font-size: var(--t-micro);
                   color: var(--ink-soft); }
        .keys .dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
        .keys .bar { width: 16px; height: 2px; flex: none; border-radius: 1px; }
      `}</style>
    </figure>
  );
}
