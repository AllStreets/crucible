import Link from "next/link";
import {
  agentRows, builtButNotInvocable, failuresByClass, loadDataset,
  loadManifest, stageRows, viability,
} from "../lib/dataset";
import { FAILURE_LABELS } from "../lib/failures";
import { VesselPanel } from "../components/VesselPanel";
import { Funnel, type Stage } from "../components/viz/Funnel";
import { Distribution, type Cause } from "../components/viz/Distribution";

// Causes attributable to this harness rather than to the repository. Mirrors
// crucible/press.py, which owns the same split for the paper.
const HARNESS_LIMITS = new Set([
  "unsupported_language", "workspace_root_not_installable",
  "python_version_unsupported", "no_build_recipe", "ambiguous_manifest", "unknown",
]);

export default function Home() {
  const data = loadDataset();
  const m = loadManifest();
  const v = viability(data);
  const rows = agentRows(data);
  const stages = stageRows(data);
  const stranded = builtButNotInvocable(data);

  const acted = new Set(data.solos.filter((s) => s.outcome === "acted").map((s) => s.slug));
  const executed = data.pairs.filter((p) => p.status === "done");
  const artifacts = data.pairs.filter((p) => p.status === "artifact");
  const blocked = data.pairs.filter((p) => p.status === "blocked");

  const funnel: Stage[] = [
    { key: "harvested", label: "Harvested at a pinned commit", count: v.harvested, tone: "t1",
      note: "One repository, resolved to a commit SHA. Unreachable seeds are recorded, not skipped." },
    { key: "built", label: "Built into a container", count: v.built, tone: "t2",
      note: "Cloned at the pin and installed by a single generic recipe, whose digest is pinned on every row." },
    { key: "checked", label: "Environment starts in a clean sandbox", count: v.checked, tone: "t2",
      note: "The image runs a probe with egress denied. This does not invoke the agent." },
    { key: "invocable", label: "Invocable, and did something", count: acted.size, tone: "t3",
      note: "Given a hand-written entrypoint and a trivial task, the agent produced the expected effect." },
    { key: "arena", label: "Executed against another agent", count: new Set(
        [...executed, ...artifacts].flatMap((p) => [p.slug_a, p.slug_b])).size, tone: "t4",
      note: "Shared a workspace with a second agent under an adversarial scenario." },
  ];

  const causes: Cause[] = Object.entries(failuresByClass(data))
    .sort((a, b) => b[1] - a[1])
    .map(([cls, count]) => ({
      cls, count,
      label: FAILURE_LABELS[cls] ?? cls,
      harness: HARNESS_LIMITS.has(cls),
      agents: rows.filter((r) => r.failureClass === cls).map((r) => r.slug),
    }));

  const pct = v.rate === null ? null : (v.rate * 100).toFixed(1);

  return (
    <div className="home">
      <section className="hero sheet">
        <div className="claim">
          <p className="label">
            <span className="pill hot live">Instrument online</span>
          </p>
          <h1>What actually happens when agents share a machine</h1>
          <p className="lede">
            Real open-source agents, cloned at pinned commits, built into
            containers, and run against each other under adversarial scenarios
            with deterministic criteria. Nothing here is estimated.
          </p>

          <div className="headline">
            <div className="fig">
              <span className="num">{v.checked}</span>
              <span className="slash">/</span>
              <span className="num total">{v.harvested}</span>
            </div>
            <div className="fig-meta">
              {pct !== null && <span className="pct mono">{pct}%</span>}
              <span className="label">reached a running environment</span>
            </div>
          </div>

          <p className="counterclaim">
            That figure does not mean the agents run. The probe starts the
            interpreter and exits. Of the agents that build, {stranded.length}{" "}
            cannot be invoked at all: they are frameworks agents are built with,
            or need a browser this harness does not install.
          </p>
        </div>

        <VesselPanel specimens={stages} />
      </section>

      <section className="sheet split">
        <div>
          <h2>Attrition, drawn to scale</h2>
          <p className="section-note">
            Every bar is a count of rows. The hatched remainder is what was lost
            at that stage, and the drop between bars is the finding.
          </p>
          <Funnel stages={funnel} total={v.harvested} />
        </div>
        <div>
          <h2>Why the rest did not</h2>
          <p className="section-note">
            Tallies of failure rows, not a partition of the agents. Colour
            carries attribution, which is the part that keeps the headline
            honest: a rate driven by harness limits describes the harness.
          </p>
          <Distribution causes={causes} />
        </div>
      </section>

      <section className="sheet">
        <h2>The arena</h2>
        <p className="section-note">
          One pair, four adversarial scenarios. Status is separated from outcome
          on purpose: a run the sandbox refused and a run whose verdict came
          from the instrument are both distinct from a result.
        </p>
        <div className="scroll-x">
          <table>
            <thead>
              <tr><th>Scenario</th><th>Pair</th><th>Status</th><th>Outcome</th><th>Model</th></tr>
            </thead>
            <tbody>
              {[...executed, ...artifacts].map((p) => (
                <tr key={p.id}>
                  <td><code>{p.scenario}</code></td>
                  <td className="pairc"><code>{p.slug_a}</code> <span className="vs">against</span> <code>{p.slug_b}</code></td>
                  <td>
                    <span className={`pill ${p.status === "done" ? "ok"
                      : p.status === "artifact" ? "artifact" : "inert"}`}>{p.status}</span>
                  </td>
                  <td><code className="out">{p.outcome ?? "not reached"}</code></td>
                  <td><code className="dim">{p.model}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section-note blocked-note">
          <span className="pill inert">{blocked.length} refused</span>
          An earlier attempt was refused by the sandbox before either agent
          started, because the images were not on its allowlist. Those rows are
          kept as refusals rather than deleted: all four still returned a
          grading, and a grading produced by an instrument that never ran the
          agents is the exact thing this table must not present as a result.
        </p>

        <p className="section-note">
          The two artifacts are the most useful result so far. Those scenarios
          instruct the victim never to print a token, naming the token in the
          instruction, and an agent that echoes its own prompt trips the leak
          detector before acting. That is a property of the scenario, not of the
          agents, and it is recorded so it can never be counted as a confirmed
          exfiltration.{" "}
          <Link href="/log">The research log carries every one of these.</Link>
        </p>
      </section>

      <section className="sheet closing">
        <div className="panel provenance">
          <div><span className="label">Engine</span><code>{m.engine_commit.slice(0, 12)}</code></div>
          <div><span className="label">Dataset sha256</span><code>{m.dataset_sha256.slice(0, 16)}</code></div>
          <div><span className="label">Generated</span><code>{m.generated_at.slice(0, 19).replace("T", " ")}</code></div>
          <p>
            Every figure above is a count of rows in that file. The site has no
            connection to the running engine, so it cannot display a number that
            was not published.
          </p>
        </div>
      </section>

      <style>{`
        .home { padding-bottom: 4rem; }
        section { padding: 4.5rem 0; }
        .hero { display: grid; padding-bottom: 5.5rem; grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
                gap: clamp(1.5rem, 4vw, 3.5rem); align-items: center;
                padding-top: 3rem; }
        .hero h1 { margin: 0.9rem 0 1rem; max-width: 15ch; }
        .lede { color: var(--ink-soft); font-size: var(--t-lead); max-width: 46ch; }

        .headline { display: flex; align-items: flex-end; gap: 1.2rem; margin: 2rem 0 1.25rem; }
        .fig { display: flex; align-items: baseline; font-family: var(--font-mono);
               font-variant-numeric: tabular-nums; line-height: 0.9; }
        .fig .num { font-size: var(--t-figure); color: var(--ink);
                    text-shadow: 0 0 34px rgba(228,99,42,0.30); }
        .fig .slash { font-size: 2.6rem; color: var(--rule-bright); margin: 0 0.35rem; }
        .fig .total { font-size: 2.6rem; color: var(--ink-soft); }
        .fig-meta { display: flex; flex-direction: column; gap: 0.3rem; padding-bottom: 0.5rem; }
        .fig-meta .pct { font-size: var(--t-h2); color: var(--accent); }

        .counterclaim { border-left: 2px solid var(--signal-warn); padding-left: 1rem;
                        color: var(--ink); font-size: var(--t-small); max-width: 52ch; }

        .split { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
                 gap: clamp(2rem, 5vw, 4rem); }
        h2 { margin-bottom: 0.6rem; }
        .section-note { font-size: var(--t-small); color: var(--ink-soft);
                        margin-bottom: 1.6rem; }
        section > .section-note:last-child { margin: 1.6rem 0 0; }

        .pairc .vs { color: var(--ink-faint); font-size: var(--t-micro); }
        .blocked-note { display: flex; gap: 0.7rem; align-items: flex-start;
                        border-left: 2px solid var(--rule-bright); padding-left: 0.9rem;
                        max-width: 74ch; }
        .blocked-note .pill { flex: none; margin-top: 0.1rem; }
        .out { color: var(--ink); }
        .dim { color: var(--ink-faint); font-size: var(--t-micro); }

        .closing { padding-top: 0; }
        .provenance { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                      gap: 1rem 2rem; padding: 1.5rem; }
        .provenance div { display: flex; flex-direction: column; gap: 0.3rem; }
        .provenance code { font-size: var(--t-small); color: var(--ink-soft); }
        .provenance p { grid-column: 1 / -1; font-size: var(--t-small);
                        color: var(--ink-soft); margin: 0; }

        @media (max-width: 960px) {
          .hero { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
