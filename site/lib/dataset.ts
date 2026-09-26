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
export interface EntrypointRow {
  id: number; slug: string; command: string[]; env_required: string[];
  workspace: string; notes: string; authored_by: string; at: string;
}
export interface SoloRow {
  id: number; slug: string; entrypoint: number;
  outcome: "acted" | "ran_no_effect" | "failed";
  failure_class: string | null; evidence_ref: string | null;
  model: string | null; base_url: string | null; duration_ms: number | null; at: string;
}
export interface PairRow {
  id: number; slug_a: string; slug_b: string; scenario: string;
  sandbox_run_id: string | null;
  status: "queued" | "running" | "done" | "lost" | "blocked" | "artifact";
  outcome: string | null; blocked_reason: string | null;
  transcript_ref: string | null; model: string | null; at: string;
}

export interface Dataset {
  candidates: Candidate[];
  builds: Build[];
  env_checks: EnvCheck[];
  unresolved: Unresolved[];
  entrypoints: EntrypointRow[];
  solos: SoloRow[];
  pairs: PairRow[];
}

export interface Manifest {
  generated_at: string;
  engine_commit: string;
  dataset_sha256: string;
  counts: Record<string, number>;
  /** How many papers verified and were written. Zero is a legitimate state
   *  and the papers page renders it, rather than an empty template presented
   *  as a published result. */
  papers_published: number;
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

/** The stage each agent actually reached, which is what the vessel draws.
 *
 *  0 harvested, 1 built, 2 environment checked, 3 invocable (solo acted),
 *  4 entered the arena. An agent never rises above the stage its rows support. */
export interface StageRow {
  slug: string;
  stage: 0 | 1 | 2 | 3 | 4;
  label: string;
  failure: string | null;
}

const STAGE_LABELS = [
  "harvested only",
  "built",
  "environment checked",
  "invocable, solo acted",
  "entered the arena",
] as const;

export function stageRows(d: Dataset): StageRow[] {
  const arena = new Set<string>();
  for (const p of d.pairs) {
    if (p.status === "done" || p.status === "artifact") {
      arena.add(p.slug_a); arena.add(p.slug_b);
    }
  }
  const acted = new Set(
    d.solos.filter((s) => s.outcome === "acted").map((s) => s.slug));
  const checked = new Set(
    d.env_checks.filter((e) => e.status === "passed").map((e) => e.build));

  return d.candidates.map((c) => {
    const build = d.builds.find((b) => b.candidate === c.slug);
    let stage: StageRow["stage"] = 0;
    if (build?.status === "built") stage = 1;
    if (build?.image_digest && checked.has(build.image_digest)) stage = 2;
    if (acted.has(c.slug)) stage = 3;
    if (arena.has(c.slug)) stage = 4;
    return {
      slug: c.slug,
      stage,
      label: STAGE_LABELS[stage],
      failure: build?.failure_class ?? null,
    };
  });
}

/** Agents that build and install cleanly and still cannot be invoked.
 *  The count of these is a finding: a framework is not an agent. */
export function builtButNotInvocable(d: Dataset): StageRow[] {
  return stageRows(d).filter((r) => r.stage === 2);
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


export interface PaperMeta {
  slug: string;
  title: string;
  abstract: string;
  generated_at: string;
  filename: string;
  word_count: number;
  sha256: string;
}

/** The published papers, read from the index the engine writes.
 *
 *  Never a hand-maintained list. A paper appears here the moment it generates
 *  and verifies, and vanishes the moment it stops, which is the only way a
 *  list of papers stays true as the research grows. */
export function loadPapers(): PaperMeta[] {
  try {
    return JSON.parse(
      readFileSync(join(process.cwd(), "public", "papers", "index.json"), "utf8"),
    ) as PaperMeta[];
  } catch {
    // An absent index means nothing has been published yet, which is a state
    // the page renders rather than an error.
    return [];
  }
}

export function loadPaperBody(filename: string): string {
  return readFileSync(join(process.cwd(), "public", "papers", filename), "utf8");
}
