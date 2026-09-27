import Link from "next/link";
import {
  agentRows, builtButNotInvocable, earnedVerdicts, failuresByClass, loadDataset,
  loadManifest, runsByScenario, scenarioInfo, viability, pairKey,
} from "../lib/dataset";
import { FAILURE_LABELS } from "../lib/failures";
import { StripChart } from "../components/viz/StripChart";
import { Attrition } from "../components/viz/Attrition";
import { DefectTimeline } from "../components/DefectTimeline";
import { RunLedger } from "../components/RunLedger";
import { Haze } from "../components/viz/Haze";
import { Rail } from "../components/Rail";
import { VerdictMatrix } from "../components/viz/VerdictMatrix";
import { pairSummaries } from "../lib/dataset";

const HARNESS_LIMITS = new Set(["unsupported_language", "workspace_root_not_installable", "python_version_unsupported", "no_build_recipe", "ambiguous_manifest", "host_out_of_disk", "unknown"]);

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
  // The classifier explains a held verdict in the same words whichever
  // scenario produced it, because the shape it describes is the same one. The
  // first version printed that sentence under every scenario, which set the
  // identical line out four times and read as filler rather than as evidence.
  // Each distinct explanation now appears once, under the first scenario it
  // applies to; the rest carry the counts and the strength, which do differ.
  const scenarioNames = Object.keys(by).sort();
  const seenNote = new Set<string>();
  const notes: Record<string, string> = {};
  for (const name of scenarioNames) {
    const runs = by[name];
    const note = (runs[runs.length - 1].blocked_reason ?? "").split(". ").slice(0, 2).join(". ");
    if (note && !seenNote.has(note)) { seenNote.add(note); notes[name] = note; }
  }
  const causes = Object.entries(failuresByClass(data)).sort((a, b) => b[1] - a[1]);
  const pct = v.rate === null ? null : (v.rate * 100).toFixed(1);
  const research = m.research ?? {};
  // The scheduler reported itself loaded and healthy for a day while having
  // executed nothing, and this line read "running unattended" on the strength
  // of passes a person had started. It now says so only when the scheduler
  // has actually produced one.
  const unattended = (research.unattended_passes ?? 0) > 0;
  let fig = 0; const F = () => ++fig;

  const sections = [
    { id: "trace", label: "The trace" }, { id: "verdicts", label: "Verdicts" },
    ...(pairSummaries(data).length > 1 ? [{ id: "matrix", label: "Matrix" }] : []),
    { id: "attrition", label: "Attrition" }, { id: "causes", label: "Causes" },
    { id: "runs", label: "Latest runs" }, { id: "log", label: "Log" },
  ];

  return (
    <div className="record">
      <header className="hero">
        <Haze />
        <div className="inner sheet">
          <div>
            <div className="eyebrow"><span className="label">Instrument record</span></div>
            <h1><span className="line">What actually</span><span className="line">happens when agents</span><span className="line">share a machine.</span></h1>
            <p className="lede">Real open-source agents, cloned at pinned commits, built into containers, and run against each other under adversarial scenarios with deterministic criteria. Nothing here is estimated; every figure is a count of rows you can open.</p>
            <p className="status">
              <span className={`state ${unattended ? "hot live" : research.last_pass ? "active" : "inert"}`}>{unattended ? "research running unattended" : research.last_pass ? "research runs when started" : "no pass yet"}</span>
              {research.last_pass && <span className="mono faint">last pass {research.last_pass.slice(0, 16).replace("T", " ")} UTC{unattended && research.cadence_hours ? `, every ${research.cadence_hours} hours` : ""}</span>}
              {research.last_pass_pushed === false && <span className="state stop">last pass did not reach the remote</span>}
            </p>
          </div>
          <div className="figures">
            <div><span className="figure">{v.checked}<span className="of">of</span>{v.harvested}</span><span className="cap">agents whose container environment starts{pct !== null ? `, ${pct}%` : ""}</span></div>
            <div><span className="figure">{acted.size}</span><span className="cap">can be invoked and do a task on command</span></div>
            <div><span className="figure earned">{earned.length}</span><span className="cap">verdicts earned, {strong.length} strong</span></div>
            <div><span className="figure hot">{confirmed.length}</span><span className="cap">attacks confirmed by a side effect</span></div>
          </div>
        </div>
      </header>

      <div className="sheet paper-grid">
        <Rail items={sections} />
        <div>
          <p className="counter"><span>That first figure does not mean the agents run. Of the agents that build, {stranded.length} cannot be invoked at all: they are frameworks agents are built with, or need a browser this harness does not install. {inArena.size} have been run against another agent.</span></p>

          <section className="block" id="trace" data-reveal>
            <h2>Every run, in order.</h2>
            <p className="deck">A tick per run in its scenario's lane, coloured by what it established. The newest pulses. This figure grows on its own as the research runs.</p>
            <figure className="fig">
              <StripChart runs={data.pairs} />
              <figcaption><b>Figure {F()}</b><span>{data.pairs.length} runs across {Object.keys(by).length} scenarios: {earned.length} verdicts, {artifacts.length} instrument artifacts never counted, {blocked.length} refused before the agents started.</span></figcaption>
            </figure>
            <div className="legend"><span className="state done">verdict</span><span className="state fail">attack confirmed</span><span className="state artifact">instrument artifact</span><span className="state blocked">refused</span></div>
          </section>

          <section className="block" id="verdicts" data-reveal>
            <h2>The current verdict, per scenario.</h2>
            <p className="deck">The newest run decides, so a regression is never hidden behind an earlier success. Strength says whether the victim engaged with the planted material before the side effect failed to occur.</p>
            <div className="spec">
              {scenarioNames.map((name) => {
                const runs = by[name]; const cur = runs[runs.length - 1]; const info = scenarioInfo(name);
                const note = notes[name];
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

          {pairSummaries(data).length > 1 && (
            <section className="block" id="matrix" data-reveal>
              <h2>Every pair, every scenario.</h2>
              <p className="deck">The newest run in each cell. A new agent adds a row for every pair it joins; a new scenario adds a column.</p>
              <figure className="fig"><VerdictMatrix data={data} /><figcaption><b>Figure {F()}</b><span>{pairSummaries(data).length} pairs across {Object.keys(by).length} scenarios.</span></figcaption></figure>
            </section>
          )}

          <section className="block" id="attrition" data-reveal>
            <h2>Attrition, to scale.</h2>
            <p className="deck">Getting an agent to the starting line is the hard part, and nobody had published how hard. The band between two bars is what was lost there.</p>
            <figure className="fig">
              <Attrition stages={[
                { key: "harvested", label: "harvested", count: v.harvested, tone: "#3E6E8E" },
                { key: "built", label: "built", count: v.built, tone: "#34A48F" },
                { key: "checked", label: "env starts", count: v.checked, tone: "#34A48F" },
                { key: "invocable", label: "invocable", count: acted.size, tone: "#C9922A" },
                { key: "arena", label: "in the arena", count: inArena.size, tone: "#E4632A" },
              ]} />
              <figcaption><b>Figure {F()}</b><span>Each bar is a count of rows; the width is its share of the agents harvested.</span></figcaption>
            </figure>
          </section>

          <section className="block" id="causes" data-reveal>
            <h2>Why the rest did not.</h2>
            <p className="deck">Tallies of failure rows, not a partition of the agents. Attribution is what keeps the headline honest: a rate driven by harness limits describes the harness.</p>
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
          </section>

          <section className="block" id="runs" data-reveal>
            <h2>Latest runs.</h2>
            <p className="deck">Status is separated from outcome on purpose. A run the sandbox refused, and a run whose verdict came from the instrument rather than the agents, are both distinct from a result, and neither ever enters a rate. <Link href="/pairs/">The whole ledger.</Link></p>
            <RunLedger runs={data.pairs} limit={8} />
          </section>

          <section className="block" id="log" data-reveal>
            <h2>What running it cost the instrument.</h2>
            <p className="deck">The engine was reviewed eight times before it was run against a live daemon. Running it found what reading had not, and the log keeps each one, retractions included. <Link href="/log/">The whole log.</Link></p>
            <DefectTimeline limit={3} />
          </section>

          <section className="closing" data-reveal>
            <h2>Nothing here is estimated.</h2>
            <p className="lede" style={{ marginTop: "1rem" }}>Every number on this page resolves to a row in a file with a digest in the footer, produced by an engine at a commit named beside it, by a pass whose parameters are published with the dataset. <Link href="/instrument/">How the research runs, and how to change what it runs.</Link></p>
          </section>
        </div>
      </div>

      <style>{`
        .faint { color: var(--ink-faint); font-size: var(--t-micro); }
        .small { font-size: var(--t-micro); }
        .figure.small { font-size: 2.4rem; line-height: 1; }
        .counter { margin-top: 2.5rem; padding: 1.4rem 0; border-top: var(--hair) solid var(--rule); border-bottom: var(--hair) solid var(--rule); font-family: var(--font-display); font-style: italic; font-size: var(--t-lead); max-width: none; color: var(--ink-soft); }
        .counter span { display: block; max-width: 62ch; }
        .legend { display: flex; gap: 1.6rem; flex-wrap: wrap; margin-top: 0.9rem; }
        .causes .k { padding-top: 0.6rem; }
        .contents { display: contents; }
      `}</style>
    </div>
  );
}
