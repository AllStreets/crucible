import { readFileSync } from "node:fs";
import { join } from "node:path";

/** Human-readable names for failure classes, read from what the engine
 *  published rather than retyped here.
 *
 *  crucible/failures.py owns these strings. A copy in TypeScript would drift
 *  from it silently, and the first symptom would be a page describing a
 *  failure as something the engine never meant. */
export const FAILURE_LABELS: Record<string, string> = JSON.parse(
  readFileSync(join(process.cwd(), "public", "data", "labels.json"), "utf8"),
);
