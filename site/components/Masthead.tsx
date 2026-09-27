import Link from "next/link";
import { loadManifest } from "../lib/dataset";
import { PaletteButton } from "./PaletteButton";

const SECTIONS = [
  { href: "/explorer", label: "Explorer" },
  { href: "/pairs", label: "Pairs" },
  { href: "/agents", label: "Agents" },
  { href: "/findings", label: "Findings" },
  { href: "/papers", label: "Papers" },
  { href: "/instrument", label: "Instrument" },
  { href: "/log", label: "Log" },
];

export function Masthead() {
  const m = loadManifest();
  return (
    <header className="masthead">
      <div className="inner sheet">
        <Link href="/" className="wordmark">
          <span className="glyph" aria-hidden="true" />
          CRUCIBLE
        </Link>
        <nav>
          {SECTIONS.map((s) => <Link key={s.href} href={s.href}>{s.label}</Link>)}
        </nav>
        <PaletteButton />
        <span className="stamp label">
          <span className="pill ok live">dataset</span>
          {m.generated_at.slice(0, 10)}
        </span>
      </div>
      <style>{`
        .masthead { position: sticky; top: 0; z-index: 20;
          background: color-mix(in srgb, var(--ground) 88%, transparent);
          backdrop-filter: blur(14px);
          border-bottom: var(--hair) solid var(--rule); }
        .masthead .inner { display: flex; align-items: center; gap: 2rem;
          padding-top: 0.85rem; padding-bottom: 0.85rem; }
        .wordmark { display: flex; align-items: center; gap: 0.6rem;
          font-family: var(--font-display); font-size: 1rem; font-weight: 600;
          letter-spacing: 0.24em; text-decoration: none; white-space: nowrap; }
        .glyph { width: 9px; height: 9px; background: var(--accent);
          box-shadow: var(--glow-accent);
          clip-path: polygon(50% 0, 100% 100%, 0 100%); }
        .masthead nav { display: flex; gap: 1.35rem; flex-wrap: wrap; margin-right: auto; }
        .masthead nav a { font-size: var(--t-small); color: var(--ink-soft);
          text-decoration: none; padding-bottom: 3px;
          border-bottom: var(--hair) solid transparent; transition: color 160ms; }
        .masthead nav a:hover { color: var(--ink); border-bottom-color: var(--accent); }
        .stamp { display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; }
        @media (max-width: 900px) {
          .masthead { position: static; }
          .masthead .inner { flex-wrap: wrap; gap: 0.7rem 1.2rem; }
          .stamp { width: 100%; }
        }
      `}</style>
    </header>
  );
}
