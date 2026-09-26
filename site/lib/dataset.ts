import { readFileSync } from "node:fs";
import { join } from "node:path";

/** The shapes the engine publishes. Kept deliberately loose on fields the site
 *  does not read, so adding a column upstream never breaks the build. */
export interface Candidate {
  id: number; slug: string; source: string; repo_url: string;
  commit_sha: string; at: string;
}
export interface Build {
  id: number; candidate: string; commit_sha: string | null;
  status: "built" | "failed"; failure_class: string | null;
  image_digest: string | null; log_ref: string | null;
  recipe_sha: string | null; at: string;
}
export interface EnvCheck {
  id: number; build: string; status: "passed" | "failed";
  failure_class: string | null; duration_ms: number | null;
  model: string | null; base_url: string | null; at: string;
}
export interface Unresolved { id: number; seed_url: string; reason: string; at: string }

export interface Dataset {
  candidates: Candidate[];
  builds: Build[];
  env_checks: EnvCheck[];
  unresolved: Unresolved[];
}

export interface Manifest {
  generated_at: string;
  engine_commit: string;
  dataset_sha256: string;
  counts: Record<string, number>;
  /** False when the record could not support a paper, in which case none was
   *  written. An empty template rendered as a published result would be the
   *  same failure as a number with no row behind it. */
  paper_published: boolean;
}

const DATA_DIR = join(process.cwd(), "public", "data");

function read<T>(name: string): T {
  try {
    return JSON.parse(readFileSync(join(DATA_DIR, name), "utf8")) as T;
  } catch (cause) {
    // Deliberately fatal, and deliberately loud.
    //
    // Returning an empty dataset would render a complete site full of zeros,
    // and a zero on this site is a finding. A build that silently publishes
    // "0 agents built" because a file was missing is worse than a build that
    // fails, because nobody would know to look.
    throw new Error(
      `public/data/${name} is missing or unreadable. Run: crucible publish ` +
      `--db <store> --out site/public/data`,
      { cause },
    );
  }
}

export function loadDataset(): Dataset { return read<Dataset>("dataset.json"); }
export function loadManifest(): Manifest { return read<Manifest>("manifest.json"); }
export function loadSchema(): Record<string, string[]> {
  return read<Record<string, string[]>>("schema.json");
}

export interface Viability {
  harvested: number;
  built: number;
  checked: number;
  unresolved: number;
  /** null rather than NaN when nothing was harvested. A rate over an empty
   *  denominator is not zero percent, it is undefined, and rendering it as
   *  "0.0%" would state a finding that was never measured. */
  rate: number | null;
}

export function viability(d: Dataset): Viability {
  const harvested = d.candidates.length;
  const built = d.builds.filter((b) => b.status === "built").length;
  const checked = d.env_checks.filter((e) => e.status === "passed").length;
  return {
    harvested,
    built,
    checked,
    unresolved: d.unresolved.length,
    rate: harvested === 0 ? null : checked / harvested,
  };
}

/** Tallies of recorded failure rows, by class.
 *
 *  These are not a partition of the candidates. A candidate that fails to
 *  build contributes one build row and no check row; one that builds and then
 *  fails the check contributes a row to each; one that passes contributes
 *  neither. Any surface rendering this must say so. */
export function failuresByClass(d: Dataset): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const row of [...d.builds, ...d.env_checks]) {
    if (!row.failure_class) continue;
    counts[row.failure_class] = (counts[row.failure_class] ?? 0) + 1;
  }
  return counts;
}

/** One row per agent, joining candidate to build to check.
 *
 *  env_checks key on the image digest rather than the build id, so the join
 *  goes through image_digest. A build with no digest never produced an image
 *  and therefore can have no check. */
export interface AgentRow {
  slug: string;
  repoUrl: string;
  commitSha: string;
  status: "built" | "failed";
  failureClass: string | null;
  imageDigest: string | null;
  checkPassed: boolean;
  checkDurationMs: number | null;
}

export function agentRows(d: Dataset): AgentRow[] {
  const byDigest = new Map(d.env_checks.map((e) => [e.build, e]));
  return d.candidates.map((c) => {
    const build = d.builds.find((b) => b.candidate === c.slug);
    const check = build?.image_digest ? byDigest.get(build.image_digest) : undefined;
    return {
      slug: c.slug,
      repoUrl: c.repo_url,
      commitSha: c.commit_sha,
      status: build?.status ?? "failed",
      failureClass: build?.failure_class ?? null,
      imageDigest: build?.image_digest ?? null,
      checkPassed: check?.status === "passed",
      checkDurationMs: check?.duration_ms ?? null,
    };
  });
}
