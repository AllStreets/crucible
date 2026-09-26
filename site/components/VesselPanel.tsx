"use client";

import dynamic from "next/dynamic";
import type { Specimen } from "./viz/Vessel";

// The canvas is client-only and heavy, so it loads after the page is readable.
// The fallback is a real frame rather than a spinner: the page at rest must
// still show what it is.
const Vessel = dynamic(() => import("./viz/Vessel").then((m) => m.Vessel), {
  ssr: false,
  loading: () => <div className="vessel-skeleton" />,
});

// Must match STAGE_COLOR in viz/Vessel.tsx. A legend whose swatch differs from
// the mark it names is worse than no legend.
const LEGEND = [
  { tone: "#3E6E8E", text: "harvested" },
  { tone: "#2E9C8E", text: "built and checked" },
  { tone: "#C8922A", text: "invocable" },
  { tone: "#FF8A3D", text: "in the arena" },
];

export function VesselPanel({ specimens }: { specimens: Specimen[] }) {
  return (
    <figure className="vessel-panel panel">
      <figcaption>
        <span className="label">The vessel</span>
        <span className="cap">
          One specimen per agent, at the height of the stage it survived to
        </span>
      </figcaption>
      <Vessel specimens={specimens} />
      <ul className="legend">
        {LEGEND.map((l) => (
          <li key={l.text}>
            <span className="dot" style={{ background: l.tone, boxShadow: `0 0 8px ${l.tone}` }} />
            <span>{l.text}</span>
          </li>
        ))}
      </ul>
      <style>{`
        .vessel-panel { margin: 0; padding: 1rem 1rem 0.85rem; overflow: hidden; }
        .vessel-panel figcaption { display: flex; flex-direction: column; gap: 0.2rem;
                                   margin-bottom: 0.4rem; }
        .vessel-panel .cap { font-size: var(--t-micro); color: var(--ink-soft); }
        .vessel-skeleton { height: clamp(360px, 52vh, 540px);
          background: radial-gradient(ellipse 60% 50% at 50% 100%,
            rgba(228,99,42,0.10), transparent 70%); }
        .legend { list-style: none; display: flex; flex-wrap: wrap; gap: 0.5rem 1.1rem;
                  margin: 0.5rem 0 0; padding: 0.6rem 0 0;
                  border-top: var(--hair) solid var(--rule); }
        .legend li { display: flex; align-items: center; gap: 0.45rem;
                     font-family: var(--font-mono); font-size: var(--t-micro);
                     color: var(--ink-soft); letter-spacing: 0.06em; }
        .legend .dot { width: 7px; height: 7px; border-radius: 50%; }
      `}</style>
    </figure>
  );
}
