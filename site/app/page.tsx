import Link from "next/link";
import {
  agentRows, builtButNotInvocable, earnedVerdicts, failuresByClass, loadDataset,
  loadManifest, stageRows, viability,
} from "../lib/dataset";
import { FAILURE_LABELS } from "../lib/failures";
import { GraphPanel } from "../components/GraphPanel";
import { buildGraph, legendFor, stageLegend } from "../lib/graph";
import { Telemetry } from "../components/Telemetry";
import { RunLedger } from "../components/RunLedger";
import { VerdictGrid } from "../components/VerdictGrid";
import { Attrition } from "../components/viz/Attrition";
import { Distribution, type Cause } from "../components/viz/Distribution";
import { DefectTimeline } from "../components/DefectTimeline";

const HARNESS_LIMITS = new Set([
  "unsupported_language", "workspace_root_not_installable",
  "python_version_unsupported", "no_build_recipe", "ambiguous_manifest", "unknown",
]);

export default function Console() {
  const data = loadDataset();
  const m = loadManifest();
  const v = viability(data);
  const rows = agentRows(data);
  const stages = stageRows(data);
  const stranded = builtButNotInvocable(data);
  const graph = buildGraph(data);

  const acted = new Set(data.solos.filter((s) => s.outcome === "acted").map((s) => s.slug));
  const earned = earnedVerdicts(data);
  const strong = earned.filter((p) => p.strength === "strong");
  const artifacts = data.pairs.filter((p) => p.status === "artifact");
  const blocked = data.pairs.filter((p) => p.status === "blocked");
  const inArena = new Set(data.pairs.filter((p) => p.status !== "blocked").flatMap((p) => [p.slug_a, p.slug_b]));

  const causes: Cause[] = Object.entries(failuresByClass(data)).sort((a, b) => b[1] - a[1])
    .map(([cls, count]) => ({ cls, count, label: FAILURE_LABELS[cls] ?? cls, harness: HARNESS_LIMITS.has(cls),
      agents: rows.filter((r) => r.failureClass === cls).map((r) => r.slug) }));

  const pct = v.rate === null ? null : (v.rate * 100).toFixed(1);

  return (
    <div className="console sheet">
      <section className="strip">
        <Telemetry items={[
          { label: "Agents harvested", value: v.harvested, sub: "pinned commits" },
          { label: "Environment starts", value: v.checked, sub: pct !== null ? `${pct}% of harvested` : "", tone: "cool" },
          { label: "Invocable", value: acted.size, sub: "passed the solo gate" },
          { label: "Earned verdicts", value: earned.length, sub: `${strong.length} strong`, tone: "hot" },
          { label: "Instrument artifacts", value: artifacts.length, sub: "never counted", tone: "artifact" },
          { label: "Refused", value: blocked.length, sub: "before agents started" },
        ]} />
      </section>

      <section className="hero">
        <div className="claim">
          <span className="pill hot live">Instrument online</span>
          <h1>What actually happens when agents share a machine</h1>
          <p className="lede">
            Real open-source agents, cloned at pinned commits, built into
            containers, and run against each other under adversarial scenarios
            with deterministic criteria. Nothing here is estimated.
          </p>
          <div className="headline">
            <div className="fig"><span className="num">{v.checked}</span><span className="slash">/</span><span className="num total">{v.harvested}</span></div>
            <div className="fig-meta">
              {pct !== null && <span className="pct mono">{pct}%</span>}
              <span className="label">reached a running environment</span>
            </div>
          </div>
          <p className="counterclaim">
            That figure does not mean the agents run. Of the agents that build,{" "}
            {stranded.length} cannot be invoked at all: they are frameworks agents
            are built with, or need a browser this harness does not install. Only{" "}
            {acted.size} have done a task on command, and {inArena.size} have been
            run against another agent.
          </p>
        </div>
        <GraphPanel nodes={graph.nodes} links={graph.links} stageKey={stageLegend(graph.nodes)} edgeKey={legendFor(graph.links)} />
      </section>

      <section className="grid-2 verdicts">
        <div className="stack">
          <div className="panel-head" style={{ padding: "0 0 0.6rem" }}>
            <span className="title">Current verdict per scenario</span>
            <Link href="/pairs/" className="label" style={{ color: "var(--accent)" }}>all runs</Link>
          </div>
          <VerdictGrid data={data} />
        </div>
        <div className="panel live-panel">
          <div className="panel-head">
            <span className="title">Run ledger</span>
            <span className="label">{data.pairs.length} runs recorded</span>
          </div>
          <RunLedger runs={data.pairs} limit={9} />
          <p className="note" style={{ padding: "0.7rem 1rem", borderTop: "var(--hair) solid var(--rule)" }}>
            Status is separated from outcome on purpose. A run the sandbox refused,
            and a run whose verdict came from the instrument rather than the
            agents, are both distinct from a result, and neither ever enters a rate.
          </p>
        </div>
      </section>

      <section className="grid-2">
        <div className="panel">
          <div className="panel-head"><span className="title">Attrition, drawn to scale</span><span className="label">count of rows per stage</span></div>
          <div className="panel-body">
            <Attrition stages={[
              { key: "harvested", label: "harvested", count: v.harvested, tone: "#3E6E8E" },
              { key: "built", label: "built", count: v.built, tone: "#2E9C8E" },
              { key: "checked", label: "env starts", count: v.checked, tone: "#2E9C8E" },
              { key: "invocable", label: "invocable", count: acted.size, tone: "#C8922A" },
              { key: "arena", label: "in the arena", count: inArena.size, tone: "#FF8A3D" },
            ]} />
            <p className="note" style={{ marginTop: "0.6rem" }}>
              The band between two bars is the loss at that stage. Getting an
              agent to the starting line is the hard part, and nobody had
              published how hard.
            </p>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head"><span className="title">Why the rest did not</span><span className="label">attribution in colour</span></div>
          <div className="panel-body"><Distribution causes={causes} /></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <span className="title">What running it cost the instrument</span>
          <Link href="/log/" className="label" style={{ color: "var(--accent)" }}>the whole log</Link>
        </div>
        <div className="panel-body"><DefectTimeline limit={4} /></div>
      </section>

      <section className="panel provenance">
        <div><span className="label">Engine</span><code>{m.engine_commit.slice(0, 12)}</code></div>
        <div><span className="label">Dataset sha256</span><code>{m.dataset_sha256.slice(0, 16)}</code></div>
        <div><span className="label">Generated</span><code>{m.generated_at.slice(0, 19).replace("T", " ")}</code></div>
        <p>Every figure above is a count of rows in that file. The site has no connection to the running engine, so it cannot display a number that was not published.</p>
      </section>

      <style>{`
        .console { display: flex; flex-direction: column; gap: 1.25rem; padding-bottom: 3rem; }
        .strip { padding-top: 1.25rem; }
        .hero { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
                gap: clamp(1.25rem, 3vw, 2.5rem); align-items: start; padding: 1rem 0 0.5rem; }
        .hero h1 { margin: 0.8rem 0 0.9rem; max-width: 15ch; }
        .headline { display: flex; align-items: flex-end; gap: 1.2rem; margin: 1.6rem 0 1.1rem; }
        .fig { display: flex; align-items: baseline; font-family: var(--font-mono);
               font-variant-numeric: tabular-nums; line-height: 0.9; }
        .fig .num { font-size: var(--t-figure); color: var(--ink); text-shadow: 0 0 34px rgba(228,99,42,0.30); }
        .fig .slash { font-size: 2.6rem; color: var(--rule-bright); margin: 0 0.35rem; }
        .fig .total { font-size: 2.6rem; color: var(--ink-soft); }
        .fig-meta { display: flex; flex-direction: column; gap: 0.3rem; padding-bottom: 0.5rem; }
        .fig-meta .pct { font-size: var(--t-h2); color: var(--accent); }
        .counterclaim { border-left: 2px solid var(--signal-warn); padding-left: 1rem;
                        font-size: var(--t-small); max-width: 54ch; }
        .verdicts { align-items: start; }
        .provenance { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                      gap: 1rem 2rem; padding: 1.25rem; }
        .provenance div { display: flex; flex-direction: column; gap: 0.3rem; }
        .provenance code { font-size: var(--t-small); color: var(--ink-soft); }
        .provenance p { grid-column: 1 / -1; font-size: var(--t-small); color: var(--ink-soft); }
        @media (max-width: 960px) { .hero { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}
