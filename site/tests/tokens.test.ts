import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

const tokens = readFileSync("app/tokens.css", "utf8");
const globals = readFileSync("app/globals.css", "utf8");

test("both surfaces define every generic token", () => {
  const generic = ["--ground", "--panel", "--ink", "--ink-soft", "--rule", "--accent"];
  for (const surface of ["specimen", "detector"]) {
    const after = globals.split(`data-surface="${surface}"`)[1] ?? "";
    const block = after.slice(0, after.indexOf("}"));
    for (const name of generic) {
      expect(block.includes(name), `${surface} is missing ${name}`).toBe(true);
    }
  }
});

test("the forbidden faces appear nowhere", () => {
  // Inter and Space Grotesk are the visual signature of machine-generated
  // sites, and avoiding them is a stated requirement rather than a preference.
  for (const banned of ["Inter", "Space Grotesk"]) {
    expect(tokens.includes(banned), `${banned} must not be used`).toBe(false);
    expect(globals.includes(banned), `${banned} must not be used`).toBe(false);
  }
});

test("no component-level colour is defined only inside a surface block", () => {
  // Every colour token must exist on bare :root before a surface redefines it,
  // or a page rendered before the surface attribute is applied has no colour
  // at all. This is the classic unreadable-artifact bug.
  const root = tokens.split(":root")[1] ?? "";
  for (const name of ["--specimen-ground", "--detector-ground", "--reagent"]) {
    expect(root.includes(name), `${name} must be declared on :root`).toBe(true);
  }
});

test("body paints an explicit background from a token", () => {
  // A transparent body borrows whatever ground the host paints, which is how a
  // page ends up rendering one theme's text on the other theme's background.
  expect(/body\s*\{[^}]*background:\s*var\(--ground\)/.test(globals)).toBe(true);
});
