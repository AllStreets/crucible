import { readFileSync } from "node:fs";
import { join } from "node:path";

/** Human-readable names for failure classes, read from what the engine
 *  published rather than retyped here.
 *
 *  crucible/failures.py owns these strings. A copy in TypeScript would drift
 *  from it silently, and the first symptom would be a page describing a
 *  failure as something the engine never meant. */
interface Label { label: string; attribution: "harness" | "repository" }

const RAW: Record<string, Label | string> = JSON.parse(
  readFileSync(join(process.cwd(), "public", "data", "labels.json"), "utf8"),
);

export const FAILURE_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(RAW).map(([k, v]) => [k, typeof v === "string" ? v : v.label]),
);

/** Whose side of the instrument a failure sits on, published by the engine
 *  rather than kept in a set here. Three pages kept their own copies of this
 *  and two had already fallen behind the classes added since; a rate driven by
 *  limits of this harness describes the harness, so it is not a detail a page
 *  may quietly get wrong. */
export function isHarnessLimit(cls: string): boolean {
  const v = RAW[cls];
  return typeof v === "string" ? false : v?.attribution === "harness";
}
