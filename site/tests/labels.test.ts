import { readFileSync } from "node:fs";
import { expect, test } from "vitest";

test("the site does not retype a failure label", () => {
  // crucible/failures.py owns these strings. Any label spelled out in the
  // site's own source is a second definition waiting to drift.
  const sources = ["app/page.tsx", "lib/failures.ts"];
  for (const file of sources) {
    const src = readFileSync(file, "utf8");
    expect(src.includes("No usable build recipe")).toBe(false);
    expect(src.includes("Written in a language this recipe does not build")).toBe(false);
  }
});

test("every class the engine publishes has a label", () => {
  const labels = JSON.parse(readFileSync("public/data/labels.json", "utf8"));
  const dataset = JSON.parse(readFileSync("public/data/dataset.json", "utf8"));
  const used = new Set<string>();
  for (const row of [...dataset.builds, ...dataset.env_checks]) {
    if (row.failure_class) used.add(row.failure_class);
  }
  for (const cls of used) {
    expect(labels[cls], `${cls} has no published label`).toBeTruthy();
  }
});
