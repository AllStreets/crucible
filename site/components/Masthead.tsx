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
        <Link href="/" className="wordmark"><span className="mark" aria-hidden="true" />Crucible</Link>
        <nav>{SECTIONS.map((s) => <Link key={s.href} href={s.href}>{s.label}</Link>)}</nav>
        <PaletteButton />
        <span className="stamp">record of {m.generated_at.slice(0, 10)}</span>
      </div>
    </header>
  );
}
