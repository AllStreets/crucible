import type { Dataset } from "./dataset";
import { stageRows } from "./dataset";

/** The interaction graph, derived entirely from rows.
 *
 *  Nothing here is sized, coloured or laid out by hand. As the arena grows,
 *  more agents appear, more edges appear, hubs get larger because their degree
 *  grows, and the legend still describes the picture. A visualisation that has
 *  to be recast when the data changes is a visualisation that will eventually
 *  disagree with the data.
 */

export interface GraphNode {
  id: string;
  name: string;
  stage: number;
  stageLabel: string;
  failure: string | null;
  color: string;
  /** Recomputed client-side from degree; seeded here so SSR output is stable. */
  val: number;
  repoUrl: string;
}

export interface GraphLink {
  source: string;
  target: string;
  scenario: string;
  status: string;
  outcome: string | null;
  color: string;
  width: number;
  note: string | null;
  /** Parallel runs between the same two agents fan out rather than stacking,
   *  so eight runs read as eight arcs instead of one line. The count of runs
   *  between a pair is itself a finding. */
  curvature: number;
}

/** Node colour is the stage an agent reached: cold to hot. */
export const STAGE_COLOR = [
  "#3E6E8E", // harvested only
  "#2E9C8E", // built
  "#2E9C8E", // environment checked
  "#C8922A", // invocable
  "#FF8A3D", // in the arena
] as const;

/** Edge colour is what the run established, and the ranking is deliberate:
 *  a refused run and an instrument artifact are not weaker results, they are
 *  different kinds of non-result, so neither shares a colour with a verdict. */
export const EDGE_STYLE: Record<string, { color: string; width: number; label: string }> = {
  done:     { color: "#2E9C8E", width: 2.4, label: "executed, verdict recorded" },
  artifact: { color: "#7B5CA8", width: 2.0, label: "instrument artifact, not a verdict" },
  blocked:  { color: "#3A4250", width: 1.2, label: "refused before the agents started" },
  lost:     { color: "#C6453B", width: 1.6, label: "run lost" },
  queued:   { color: "#3A4250", width: 1.0, label: "queued" },
  running:  { color: "#C8922A", width: 1.6, label: "running" },
};

export function buildGraph(d: Dataset): { nodes: GraphNode[]; links: GraphLink[] } {
  const stages = new Map(stageRows(d).map((r) => [r.slug, r]));
  const repo = new Map(d.candidates.map((c) => [c.slug, c.repo_url]));

  const nodes: GraphNode[] = d.candidates.map((c) => {
    const s = stages.get(c.slug)!;
    return {
      id: c.slug,
      name: c.slug,
      stage: s.stage,
      stageLabel: s.label,
      failure: s.failure,
      color: STAGE_COLOR[s.stage],
      val: 1,
      repoUrl: repo.get(c.slug) ?? "",
    };
  });

  // One edge per pair run. Several runs between the same two agents stay
  // several edges, because a scenario is the unit of evidence and collapsing
  // them would hide that three of four runs here established nothing.
  const parallel = new Map<string, number>();
  const links: GraphLink[] = d.pairs.map((p) => {
    const style = EDGE_STYLE[p.status] ?? EDGE_STYLE.queued;
    const key = [p.slug_a, p.slug_b].sort().join("|");
    const n = parallel.get(key) ?? 0;
    parallel.set(key, n + 1);
    // Alternate sides and widen, so arcs stay distinguishable however many
    // runs a pair accumulates.
    const curvature = n === 0 ? 0 : (n % 2 ? 1 : -1) * (0.16 + Math.floor((n - 1) / 2) * 0.17);
    return {
      curvature,
      source: p.slug_a,
      target: p.slug_b,
      scenario: p.scenario,
      status: p.status,
      outcome: p.outcome,
      color: style.color,
      width: style.width,
      note: p.blocked_reason,
    };
  });

  return { nodes, links };
}

/** Which edge kinds are actually present, so the legend describes this picture
 *  rather than every kind the schema allows. */
export function legendFor(links: GraphLink[]): { key: string; color: string; label: string }[] {
  const present = new Set(links.map((l) => l.status));
  return Object.entries(EDGE_STYLE)
    .filter(([k]) => present.has(k))
    .map(([key, v]) => ({ key, color: v.color, label: v.label }));
}

/** Stage legend, limited to stages actually reached. */
export function stageLegend(nodes: GraphNode[]): { color: string; label: string }[] {
  const seen = new Map<number, string>();
  for (const n of nodes) if (!seen.has(n.stage)) seen.set(n.stage, n.stageLabel);
  return [...seen.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([stage, label]) => ({ color: STAGE_COLOR[stage], label }));
}
