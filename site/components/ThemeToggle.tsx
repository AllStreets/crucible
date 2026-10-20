"use client";

import { useEffect, useState } from "react";
import { applyChoice, readChoice, type ThemeChoice } from "../lib/theme";

const NEXT: Record<ThemeChoice, ThemeChoice> = { system: "light", light: "dark", dark: "system" };
const LABEL: Record<ThemeChoice, string> = { system: "Theme: system", light: "Theme: light", dark: "Theme: dark" };

/** One button that cycles system, light, dark. The label says the current state. */
export function ThemeToggle() {
  const [choice, setChoice] = useState<ThemeChoice>("system");
  useEffect(() => setChoice(readChoice()), []);
  const next = () => { const c = NEXT[choice]; applyChoice(c); setChoice(c); };
  return (
    <button type="button" className="theme-toggle" onClick={next} aria-label={`${LABEL[choice]}. Switch to ${NEXT[choice]}.`} title={`${LABEL[choice]}. Click for ${NEXT[choice]}.`}>
      <span aria-hidden="true" className={`theme-glyph ${choice}`} />
      <span className="theme-word">{choice}</span>
    </button>
  );
}
