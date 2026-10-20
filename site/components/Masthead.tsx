import Link from "next/link";
import { loadManifest } from "../lib/dataset";
import { PaletteButton } from "./PaletteButton";
import { ThemeToggle } from "./ThemeToggle";

/** The masthead carries the reading journey and the two doors into the
 *  instrument. Scenarios and the log are reached from the sections of the
 *  front page that are about them, and everything on the site is in the
 *  palette, so a bar that wrapped onto a second row was spending a row to
 *  duplicate links a reader already had. */
const SECTIONS = [
  { href: "/explorer", label: "Explorer" },
  { href: "/pairs", label: "Pairs" },
  { href: "/agents", label: "Agents" },
  { href: "/findings", label: "Findings" },
  { href: "/papers", label: "Papers" },
  { href: "/instrument", label: "Instrument" },
  { href: "/control", label: "Control" },
  { href: "/propose", label: "Propose" },
];


export function Masthead() {
  const m = loadManifest();
  return (
    <header className="masthead">
      <div className="inner sheet">
        <Link href="/" className="wordmark"><span className="mark" aria-hidden="true" />Crucible</Link>
        <nav>{SECTIONS.map((s) => <Link key={s.href} href={s.href}>{s.label}</Link>)}</nav>
        <PaletteButton />
        <ThemeToggle />
        <span className="stamp">record of {m.generated_at.slice(0, 10)}</span>
      </div>
    </header>
  );
}
