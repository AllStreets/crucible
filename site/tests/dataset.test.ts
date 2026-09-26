import { expect, test } from "vitest";
import { agentRows, failuresByClass, viability, type Dataset } from "../lib/dataset";

const sample: Dataset = {
  candidates: [
    { id: 1, slug: "a", source: "github", repo_url: "https://github.com/x/a", commit_sha: "a".repeat(40), at: "" },
    { id: 2, slug: "b", source: "github", repo_url: "https://github.com/x/b", commit_sha: "b".repeat(40), at: "" },
    { id: 3, slug: "c", source: "github", repo_url: "https://github.com/x/c", commit_sha: "c".repeat(40), at: "" },
  ],
  builds: [
    { id: 1, candidate: "a", commit_sha: "a".repeat(40), status: "built", failure_class: null, image_digest: "sha256:aa", log_ref: null, recipe_sha: "sha256:r", at: "" },
    { id: 2, candidate: "b", commit_sha: "b".repeat(40), status: "failed", failure_class: "unsupported_language", image_digest: null, log_ref: null, recipe_sha: "sha256:r", at: "" },
    { id: 3, candidate: "c", commit_sha: "c".repeat(40), status: "failed", failure_class: "workspace_root_not_installable", image_digest: null, log_ref: null, recipe_sha: "sha256:r", at: "" },
  ],
  env_checks: [
    { id: 1, build: "sha256:aa", status: "passed", failure_class: null, duration_ms: 247, model: null, base_url: null, at: "" },
  ],
  unresolved: [],
};

test("viability is computed from rows, never asserted", () => {
  const v = viability(sample);
  expect(v.harvested).toBe(3);
  expect(v.built).toBe(1);
  expect(v.checked).toBe(1);
  expect(v.rate).toBeCloseTo(1 / 3);
});

test("an empty denominator gives null, not zero percent", () => {
  // A rate over nothing is undefined, not zero. Rendering it as "0.0%" would
  // state a finding that was never measured.
  const v = viability({ ...sample, candidates: [], builds: [], env_checks: [] });
  expect(v.rate).toBeNull();
});

test("failure counts are tallies of rows, not a partition of candidates", () => {
  const counts = failuresByClass(sample);
  expect(counts.unsupported_language).toBe(1);
  expect(counts.workspace_root_not_installable).toBe(1);
  // Two failure rows against three candidates. These do not sum to the
  // harvested count and no surface may present them as though they do.
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  expect(total).not.toBe(sample.candidates.length);
});

test("env checks join through the image digest, not the build id", () => {
  const rows = agentRows(sample);
  const a = rows.find((r) => r.slug === "a")!;
  expect(a.checkPassed).toBe(true);
  expect(a.checkDurationMs).toBe(247);
  // A build that produced no image can have no check.
  expect(rows.find((r) => r.slug === "b")!.checkPassed).toBe(false);
});
