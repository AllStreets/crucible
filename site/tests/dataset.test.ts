import { expect, test } from "vitest";
import { agentRows, builtButNotInvocable, failuresByClass, stageRows, viability, type Dataset } from "../lib/dataset";

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
  entrypoints: [],
  solos: [],
  pairs: [],
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


test("an agent never rises above the stage its rows support", () => {
  // The vessel draws stage as height, so a wrong stage is a visual claim that
  // an agent got further than the record says it did.
  const rows = stageRows(sample);
  const a = rows.find((r) => r.slug === "a")!;
  expect(a.stage).toBe(2); // built and checked, no solo row
  expect(rows.find((r) => r.slug === "b")!.stage).toBe(0); // failed to build
});

test("built but not invocable is its own count", () => {
  // Four of ten agents build cleanly and still cannot be invoked. A framework
  // is not an agent, and counting it as one overstates what exists.
  expect(builtButNotInvocable(sample).map((r) => r.slug)).toEqual(["a"]);
});

import { earnedVerdicts, pairSummaries, searchIndex, latestByScenario } from "../lib/dataset";

const withPairs: Dataset = {
  ...sample,
  entrypoints: [],
  solos: [{ id: 1, slug: "a", entrypoint: 1, outcome: "acted", failure_class: null, evidence_ref: null, model: "m", base_url: null, duration_ms: 10, at: "2026-09-27T00:00:00" }],
  pairs: [
    { id: 1, slug_a: "a", slug_b: "b", scenario: "state_poisoning", sandbox_run_id: "r1", status: "blocked", outcome: null, blocked_reason: "refused", transcript_ref: null, model: "m", strength: null, at: "2026-09-27T00:00:01" },
    { id: 2, slug_a: "a", slug_b: "b", scenario: "state_poisoning", sandbox_run_id: "r2", status: "artifact", outcome: "pass", blocked_reason: "instrument", transcript_ref: null, model: "m", strength: null, at: "2026-09-27T00:00:02" },
    { id: 3, slug_a: "a", slug_b: "b", scenario: "state_poisoning", sandbox_run_id: "r3", status: "done", outcome: "pass", blocked_reason: "earned", transcript_ref: null, model: "m", strength: "strong", at: "2026-09-27T00:00:03" },
    { id: 4, slug_a: "b", slug_b: "a", scenario: "secret_exfiltration", sandbox_run_id: "r4", status: "done", outcome: "pass", blocked_reason: "weak", transcript_ref: null, model: "m", strength: "weak", at: "2026-09-27T00:00:04" },
  ],
};

test("only done runs are verdicts, and strength is read from the column", () => {
  const v = earnedVerdicts(withPairs);
  expect(v.map((p) => p.id)).toEqual([3, 4]);
  expect(v.filter((p) => p.strength === "strong").length).toBe(1);
});

test("a pair is the same pair whichever way round it was recorded", () => {
  const ps = pairSummaries(withPairs);
  expect(ps.length).toBe(1);
  expect(ps[0].key).toBe("a--b");
  expect(ps[0].runs.length).toBe(4);
  expect([ps[0].earned, ps[0].artifacts, ps[0].blocked, ps[0].strong]).toEqual([2, 1, 1, 1]);
});

test("the current verdict per scenario is the newest run, not the best one", () => {
  // A console shows the latest state. If a later run were an artifact, it
  // would be the artifact that shows, so a regression is never hidden behind
  // an earlier success.
  const latest = latestByScenario(withPairs);
  expect(latest.find((p) => p.scenario === "state_poisoning")!.id).toBe(3);
});

test("the palette index reaches everything with a row", () => {
  const idx = searchIndex(withPairs);
  expect(idx.some((i) => i.kind === "agent" && i.title === "a")).toBe(true);
  expect(idx.some((i) => i.kind === "pair" && i.href === "/pairs/a--b/")).toBe(true);
  expect(idx.some((i) => i.kind === "scenario")).toBe(true);
  // A new agent in the dataset appears in the index without anyone editing it.
  const more = { ...withPairs, candidates: [...withPairs.candidates, { id: 9, slug: "z", source: "github", repo_url: "https://github.com/x/z", commit_sha: "z".repeat(40), at: "" }] };
  expect(searchIndex(more).some((i) => i.title === "z")).toBe(true);
});
