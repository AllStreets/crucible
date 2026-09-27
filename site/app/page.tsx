import Link from "next/link";
import {
  agentRows, builtButNotInvocable, earnedVerdicts, failuresByClass, loadDataset,
  loadManifest, runsByScenario, scenarioInfo, stageRows, viability, pairKey,
} from "../lib/dataset";
import { FAILURE_LABELS } from "../lib/failures";
import { StripChart } from "../components/viz/StripChart";
import { Attrition } from "../components/viz/Attrition";
import { DefectTimeline } from "../components/DefectTimeline";
import { RunLedger } from "../components/RunLedger";

const HARNESS_LIMITS = new Set(["unsupported_language", "workspace_root_not_installable", "python_version_unsupported", "no_build_recipe", "ambiguous_manifest", "unknown"]);

export default function Record() {
  const data = loadDataset(); const m = loadManifest();
  const v = viability(data);
  const rows = agentRows(data);
  const stranded = builtButNotInvocable(data);
  const acted = new Set(data.solos.filter((s) => s.outcome === "acted").map((s) => s.slug));
  const earned = earnedVerdicts(data);
  const strong = earned.filter((p) => p.strength === "strong");
  const confirmed = earned.filter((p) => p.outcome === "fail");
  const artifacts = data.pairs.filter((p) => p.status === "artifact");
  const blocked = data.pairs.filter((p) => p.status === "blocked");
  const inArena = new Set(data.pairs.filter((p) => p.status !== "blocked").flatMap((p) => [p.slug_a, p.slug_b]));
  const by = runsByScenario(data);
  const causes = Object.entries(failuresByClass(data)).sort((a, b) => b[1] - a[1]);
  const pct = v.rate === null ? null : (v.rate * 100).toFixed(1);
  const research = m.research ?? {};

  return (
    <div className="record sheet">
      <section className="block opening">
        <div className="eyebrow"><span className="label">Instrument record</span></div>
        <div className="open-grid">
          <div>
            <h1>What actually happens when agents share a machine.</h1>
            <p className="lede">Real open-source agents, cloned at pinned commits, built into containers, and run against each other under adversarial scenarios with deterministic criteria. Nothing here is estimated, and every figure on this page is a count of rows you can open.</p>
            <p className="status">
              <span className={`state ${research.last_pass ? "hot live" : "inert"}`}>{research.last_pass ? "research running unattended" : "no unattended pass yet"}</span>
              {research.last_pass && <span className="mono faint">last pass {research.last_pass.slice(0, 16).replace("T", " ")} UTC</span>}
            </p>
          </div>
          <div className="figures">
            <div><span className="figure">{v.checked}<span className="of">of</span>{v.harvested}</span><span className="cap">agents whose container environment starts{pct !== null ? `, ${pct}%` : ""}</span></div>
            <div><span className="figure">{acted.size}</span><span className="cap">can be invoked and do a task on command</span></div>
            <div><span className="figure earned">{earned.length}</span><span className="cap">verdicts earned, {strong.length} of them strong</span></div>
            <div><span className="figure hot">{confirmed.length}</span><span className="cap">attacks confirmed by a side effect</span></div>
          </div>
        </div>
        <p className="counter">That first figure does not mean the agents run. Of the agents that build, {stranded.length} cannot be invoked at all: they are frameworks agents are built with, or need a browser this harness does not install. {inArena.size} have been run against another agent.</p>
      </section>

      <section className="block">
        <div className="eyebrow"><span className="label">The trace</span><span className="label">{data.pairs.length} runs, {artifacts.length} artifacts, {blocked.length} refusals</span></div>
        <StripChart runs={data.pairs} />
        <div className="legend">
          <span className="state done">verdict</span><span className="state fail">attack confirmed</span>
          <span className="state artifact">instrument artifact, never counted</span><span className="state blocked">refused before the agents started</span>
        </div>
      </section>

      <section className="block">
        <div className="eyebrow"><span className="label">Current verdict, per scenario</span><Link href="/pairs/" className="label">every run</Link></div>
        <div className="spec">
          {Object.keys(by).sort().map((name) => {
            const runs = by[name]; const cur = runs[runs.length - 1]; const info = scenarioInfo(name);
            const note = (cur.blocked_reason ?? "").split(". ").slice(0, 2).join(". ");
            return (
              <div key={name} className="contents">
                <span className="k">{info.objective}</span>
                <div className="v scenario">
                  <h3>{info.title}</h3>
                  <p className="q">{info.question}</p>
                  <div className="row">
                    <span className={`state ${cur.status === "done" ? (cur.outcome === "fail" ? "fail" : "done") : cur.status}`}>{cur.status === "done" ? (cur.outcome === "fail" ? "attack confirmed" : "held") : cur.status}</span>
                    {cur.strength && <span className={`state ${cur.strength}`}>{cur.strength} evidence</span>}
                    <span className="mono faint">{runs.length} runs, {runs.filter((r) => r.status === "done").length} earned</span>
                    <Link href={`/pairs/${pairKey(cur.slug_a, cur.slug_b)}/#${name}`} className="mono faint">open</Link>
                  </div>
                  {note && <p className="evidence">{note}{note.endsWith(".") ? "" : "."}</p>}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="block two">
        <div>
          <div className="eyebrow"><span className="label">Attrition, to scale</span></div>
          <Attrition stages={[
            { key: "harvested", label: "harvested", count: v.harvested, tone: "#3E6E8E" },
            { key: "built", label: "built", count: v.built, tone: "#34A48F" },
            { key: "checked", label: "env starts", count: v.checked, tone: "#34A48F" },
            { key: "invocable", label: "invocable", count: acted.size, tone: "#C9922A" },
            { key: "arena", label: "in the arena", count: inArena.size, tone: "#E4632A" },
          ]} />
          <p className="note">The band between two bars is what was lost there. Getting an agent to the starting line is the hard part, and nobody had published how hard.</p>
        </div>
        <div>
          <div className="eyebrow"><span className="label">Why the rest did not</span></div>
          <div className="spec causes">
            {causes.map(([cls, n]) => (
              <div key={cls} className="contents">
                <span className="k"><span className="figure small">{n}</span></span>
                <div className="v">
                  <p>{FAILURE_LABELS[cls] ?? cls}</p>
                  <p className="mono faint small">{HARNESS_LIMITS.has(cls) ? "a limit of this harness" : "a property of the repository"} · {rows.filter((r) => r.failureClass === cls).map((r) => r.slug).join(", ")}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="note">Tallies of failure rows, not a partition of the agents. Attribution is the part that keeps the headline honest: a rate driven by harness limits describes the harness.</p>
        </div>
      </section>

      <section className="block">
        <div className="eyebrow"><span className="label">Latest runs</span><Link href="/pairs/" className="label">the ledger</Link></div>
        <RunLedger runs={data.pairs} limit={8} />
      </section>

      <section className="block">
        <div className="eyebrow"><span className="label">What running it cost the instrument</span><Link href="/log/" className="label">the whole log</Link></div>
        <DefectTimeline limit={3} />
      </section>

      <style>{`
        .record { padding-bottom: 2rem; }
        .opening { padding-top: 2.5rem; }
        .open-grid { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: clamp(2rem, 5vw, 5rem); align-items: end; margin-top: 2rem; }
        .open-grid h1 { margin-bottom: 1.2rem; }
        .status { display: flex; gap: 1rem; align-items: baseline; flex-wrap: wrap; }
        .faint { color: var(--ink-faint); font-size: var(--t-micro); }
        .small { font-size: var(--t-micro); }
        .figure.small { font-size: 2.4rem; line-height: 1; }
        .counter { margin-top: 2.5rem; padding-top: 1.25rem; border-top: var(--hair) solid var(--rule); font-family: var(--font-display); font-style: italic; font-size: var(--t-lead); max-width: 66ch; color: var(--ink-soft); }
        .legend { display: flex; gap: 1.6rem; flex-wrap: wrap; margin-top: 0.9rem; }
        .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 3.5rem; }
        .two .note { margin-top: 0.9rem; }
        .causes .k { padding-top: 0.6rem; }
        .contents { display: contents; }
        .eyebrow { margin-bottom: 1.4rem; }
        @media (max-width: 900px) { .open-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}
