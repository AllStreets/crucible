import Link from "next/link";
import { loadManifest } from "../lib/dataset";

const SECTIONS = [
  { href: "/findings", label: "Findings" },
  { href: "/papers", label: "Papers" },
  { href: "/methodology", label: "Methodology" },
  { href: "/threat-model", label: "Threat model" },
  { href: "/data", label: "Data" },
  { href: "/log", label: "Log" },
  { href: "/about", label: "About" },
];

export function Masthead() {
  const manifest = loadManifest();
  const generated = manifest.generated_at.slice(0, 10);

  return (
    <header className="masthead">
      <Link href="/" className="wordmark">CRUCIBLE</Link>
      <nav>
        {SECTIONS.map((s) => (
          <Link key={s.href} href={s.href}>{s.label}</Link>
        ))}
      </nav>
      <span className="label stamp">Dataset {generated}</span>

      <style>{`
        .masthead {
          display: flex;
          align-items: baseline;
          gap: 2rem;
          padding: 1.4rem clamp(1.25rem, 5vw, 3rem) 1rem;
          max-width: 1060px;
          margin: 0 auto;
          border-bottom: var(--rule-hair) solid var(--rule);
          position: relative;
          z-index: 2;
          background: var(--ground);
        }
        .wordmark {
          font-family: var(--font-display);
          font-size: var(--t-lead);
          font-weight: 600;
          letter-spacing: 0.14em;
          text-decoration: none;
          white-space: nowrap;
        }
        .masthead nav {
          display: flex;
          gap: 1.5rem;
          flex-wrap: wrap;
          margin-right: auto;
        }
        .masthead nav a {
          font-size: var(--t-small);
          letter-spacing: 0.02em;
          text-decoration: none;
          color: var(--ink-soft);
          padding-bottom: 2px;
          border-bottom: var(--rule-hair) solid transparent;
        }
        .masthead nav a:hover {
          color: var(--ink);
          border-bottom-color: var(--accent);
        }
        .stamp { white-space: nowrap; }
        @media (max-width: 720px) {
          .masthead { flex-wrap: wrap; gap: 0.75rem 1.25rem; }
          .stamp { width: 100%; }
        }
      `}</style>
    </header>
  );
}
