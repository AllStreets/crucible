"use client";

import { useEffect, useState } from "react";

/** The viewer's theme choice. "system" stamps nothing on <html> and lets the
 *  prefers-color-scheme media query in tokens.css decide; "light" and "dark"
 *  stamp data-theme so the choice wins over the system. Stored per browser. */
export type ThemeChoice = "system" | "light" | "dark";
import { THEME_EVENT, THEME_KEY } from "./themeBoot";
export { THEME_EVENT, THEME_KEY };

export function readChoice(): ThemeChoice {
  try {
    const t = localStorage.getItem(THEME_KEY);
    return t === "light" || t === "dark" ? t : "system";
  } catch { return "system"; }
}

export function applyChoice(choice: ThemeChoice): void {
  const root = document.documentElement;
  if (choice === "system") delete root.dataset.theme; else root.dataset.theme = choice;
  try { if (choice === "system") localStorage.removeItem(THEME_KEY); else localStorage.setItem(THEME_KEY, choice); } catch { /* storage blocked: the choice lasts this visit */ }
  window.dispatchEvent(new Event(THEME_EVENT));
}

/** A token's current value from :root, for things CSS can't reach (WebGL, three.js). */
export function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Re-renders when the effective theme changes, from the toggle or the system. */
export function useThemeVersion(): number {
  const [v, setV] = useState(0);
  useEffect(() => {
    const bump = () => setV((n) => n + 1);
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    mq.addEventListener("change", bump);
    window.addEventListener(THEME_EVENT, bump);
    return () => { mq.removeEventListener("change", bump); window.removeEventListener(THEME_EVENT, bump); };
  }, []);
  return v;
}
