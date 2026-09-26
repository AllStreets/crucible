import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

const tokens = readFileSync("app/tokens.css", "utf8");
const globals = readFileSync("app/globals.css", "utf8");

test("every colour token is declared on bare :root", () => {
  // A colour whose only definition sits inside a media or attribute block
  // never applies in the un-stamped state, which is the classic unreadable
  // page. This design commits to one dark world, so :root must be complete.
  const root = tokens.slice(tokens.indexOf(":root"), tokens.indexOf("}"));
  const required = [
    "--ground", "--panel", "--ink", "--ink-soft", "--rule", "--accent",
    "--t0", "--t1", "--t2", "--t3", "--t4", "--t5",
    "--signal-warn", "--signal-stop", "--signal-artifact",
  ];
  for (const name of required) {
    expect(root.includes(name), `${name} must be declared on :root`).toBe(true);
  }
});

test("body paints an explicit background from a token", () => {
  // The page composites over a ground the viewer paints in its own theme, so a
  // transparent body silently borrows it. A single-theme design may skip the
  // media queries but never the explicit paint.
  expect(/body\s*\{[^}]*background:\s*var\(--ground\)/.test(globals)).toBe(true);
  expect(/body\s*\{[^}]*color:\s*var\(--ink\)/.test(globals)).toBe(true);
});

test("the forbidden faces appear nowhere", () => {
  // Inter and Space Grotesk are the visual signature of machine-generated
  // sites; avoiding them is a stated requirement, not a preference.
  for (const banned of ["Inter", "Space Grotesk"]) {
    expect(tokens.includes(banned), `${banned} must not be used`).toBe(false);
    expect(globals.includes(banned), `${banned} must not be used`).toBe(false);
  }
});

test("the accent is not the default developer-site cyan or violet", () => {
  // This author's other projects use cyan and violet, and so does most of the
  // category. The thermal ramp is what makes this one identifiable as itself.
  const accent = /--accent:\s*(#[0-9A-Fa-f]{6})/.exec(tokens)?.[1] ?? "";
  expect(accent.toLowerCase()).not.toBe("#00d4ff");
  expect(accent.toLowerCase()).not.toBe("#7b5cff");
  expect(accent).toMatch(/^#[0-9A-Fa-f]{6}$/);
});

test("state is encoded in form as well as colour", () => {
  // A status that is only a hue fails for a colour-blind reader and in print.
  // The pill carries a dot and a border, so shape survives the colour.
  expect(globals.includes(".pill::before")).toBe(true);
  expect(/\.pill\s*\{[^}]*border:/.test(globals)).toBe(true);
});

test("motion respects the reduced-motion preference", () => {
  expect(globals.includes("prefers-reduced-motion")).toBe(true);
  expect(/animation-duration:\s*0\.01ms\s*!important/.test(globals)).toBe(true);
});
