import Link from "next/link";
import { failuresByClass, loadDataset, agentRows, repoNames, scenarioInfo } from "../../lib/dataset";
import { FAILURE_LABELS, isHarnessLimit } from "../../lib/failures";

export const metadata = { title: "Findings | Crucible" };

export default function Findings() {
  const data = loadDataset();
  const names = repoNames(data);
  const short = (s: string) => names[s] ?? s;

  // What the arena has established, computed rather than written. A confirmed
  // attack is the only claim here a criterion made on its own, so it is the
  // only one this section states.
  const confirmed = data.pairs.filter((p) => p.status === "done" && p.outcome === "fail");
  const scenariosHit = [...new Set(confirmed.map((c) => c.scenario))];
  const victims = [...new Set(confirmed.map((c) => c.slug_b))].sort();
  const attackers = [...new Set(confirmed.map((c) => c.slug_a))].sort();
  const everVictim = new Set(data.pairs.filter((p) => p.status !== "blocked").map((p) => p.slug_b));
  const invocable = [...new Set(data.solos.filter((s) => s.outcome === "acted").map((s) => s.slug))];
  const heldVictims = invocable.filter((a) => everVictim.has(a) && !victims.includes(a)).sort();
  const latestEntrypoint = new Map<string, string[]>();
  for (const e of [...data.entrypoints].sort((a, b) => a.id - b.id)) {
    latestEntrypoint.set(e.slug, Array.isArray(e.command) ? e.command : [String(e.command)]);
  }
  const failures = Object.entries(failuresByClass(data)).sort((a, b) => b[1] - a[1]);
  const rows = agentRows(data);
  const harness = failures.filter(([c]) => isHarnessLimit(c)).reduce((n, [, v]) => n + v, 0);
  const repo = failures.reduce((n, [, v]) => n + v, 0) - harness;
  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Findings</span><span className="label">{failures.length} classes recorded</span></div>
        <h1>Every recorded failure, and whose it is.</h1>
        <p className="lede">Tallies of failure rows, not a partition of the agents: a candidate that fails to build contributes a build row and no check row. Each class carries an attribution, because a rate driven by limits of this harness describes the harness, and a reader cannot tell that from a class name alone.</p>
        <div className="figures" style={{ marginTop: "1.5rem" }}>
          <div><span className="figure warn" style={{ color: "var(--warn)" }}>{harness}</span><span className="cap">failures that are limits of this harness</span></div>
          <div><span className="figure" style={{ color: "var(--stop)" }}>{repo}</span><span className="cap">failures that are properties of the repository</span></div>
        </div>
      </div>
      {confirmed.length > 0 && (
        <section className="block" id="arena">
          <h2>What the arena has established.</h2>
          <p className="deck">
            Every confirmation below was made by a criterion checking for a side effect, not by
            a model reading a transcript, and each was checked by hand against its own
            snapshots. Everything else on this page is about getting agents to the starting
            line; this is what happened once they were there.
          </p>

          <div className="spec">
            <span className="k">where they land</span>
            <div className="v">
              <p>
                All {confirmed.length} sit in {scenariosHit.length === 1 ? "a single scenario" : `${scenariosHit.length} scenarios`}
                {scenariosHit.map((sc) => <em key={sc}>, {scenarioInfo(sc).title}</em>)}. No other
                scenario has produced one in {data.pairs.length} runs.
              </p>
            </div>

            <span className="k">who complied</span>
            <div className="v">
              <p>
                {victims.map((v) => <code key={v}>{short(v)}</code>).reduce((acc: React.ReactNode[], el, i) => i === 0 ? [el] : [...acc, ", ", el], [])}.
                {heldVictims.length > 0 && <> Every other agent that has been cast as a victim held: {heldVictims.map((v) => short(v)).join(", ")}.</>}
              </p>
              <p className="note">
                The invocation each of them was run with is below. It is the entrypoint file as
                committed, and it is the only evidence here about why these two and not the rest.
              </p>
              {victims.map((v) => (
                <pre key={v} className="invocation"><b>{short(v)}</b>{"\n"}{(latestEntrypoint.get(v) ?? []).join(" ")}</pre>
              ))}
            </div>

            <span className="k">who induced</span>
            <div className="v">
              <p>
                {attackers.map((a) => short(a)).join(", ")}. The attacker role is filled by
                nearly every agent that has played it, which is the part worth noticing: what
                separates a pair that falls from a pair that holds is not who writes the
                instruction.
              </p>
              <p className="note">
                <Link href="/explorer/">Both roles, as a solid.</Link> Half of the orderings have
                never been run, so no agent absent from the first list has been shown to resist
                anything.
              </p>
            </div>
          </div>
        </section>
      )}

      <section className="block">
      <h2>Why most agents never got that far.</h2>
      <div className="spec">
        {failures.map(([cls, n]) => (
          <div key={cls} className="contents">
            <span className="k"><span className="figure small">{n}</span></span>
            <div className="v stack" style={{ gap: "0.6rem", paddingBottom: "0.6rem" }}>
              <h3 style={{ fontStyle: "italic" }}>{FAILURE_LABELS[cls] ?? cls}</h3>
              <p className="note"><span className={`state ${isHarnessLimit(cls) ? "warn" : "stop"}`}>{isHarnessLimit(cls) ? "a limit of this harness" : "a property of the repository"}</span> <code style={{ color: "var(--ink-faint)", marginLeft: "0.8rem" }}>{cls}</code></p>
              <ul className="agents">
                {rows.filter((r) => r.failureClass === cls).map((r) => (
                  <li key={r.slug}><a href={`/agents/${r.slug}/`}><code>{r.slug}</code></a><a href={r.repoUrl} rel="noreferrer" className="mono faint">{r.repoUrl.replace("https://github.com/", "")}</a><code className="faint">{r.commitSha.slice(0, 10)}</code></li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
      </section>
      <style>{`
        .contents { display: contents; } .figure.small { font-size: 2.4rem; line-height: 1; }
        .invocation { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-soft);
          background: var(--panel); border: var(--hair) solid var(--rule); padding: 0.8rem 0.9rem;
          white-space: pre-wrap; overflow-wrap: anywhere; margin: 0.6rem 0 0; }
        .invocation b { color: var(--ink); font-weight: 400; display: block; margin-bottom: 0.3rem; }
        .faint { color: var(--ink-faint); font-size: var(--t-micro); }
        .agents { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.35rem; }
        .agents li { display: flex; gap: 1rem; align-items: baseline; flex-wrap: wrap; font-size: var(--t-small); }
        .agents a { text-decoration: none; }
      `}</style>
    </div>
  );
}
