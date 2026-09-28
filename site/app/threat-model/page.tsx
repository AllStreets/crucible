import { Prose } from "../../components/Prose";
import { loadCoverage, loadDataset, scenarioInfo } from "../../lib/dataset";

export const metadata = { title: "Threat model | Crucible" };

export default function ThreatModel() {
  const coverage = loadCoverage();
  const data = loadDataset();
  const runsFor = (scenario: string) =>
    data.pairs.filter((p) => p.scenario === scenario && p.status === "done").length;
  const covered = coverage.filter((c) => c.covered);
  const absent = coverage.filter((c) => !c.covered);

  return (
    <div className="sheet page">
      <div className="eyebrow"><span className="label">Threat model</span></div>
      <h1>What this research covers, and what it does not</h1>

      <Prose>
        <p>
          The question is what happens when several autonomous agents share one
          machine: a filesystem, a clipboard, a set of OAuth scopes, a wallet.
          There are threat models for this. There are opinions. There is no
          dataset, and this project exists to produce one.
        </p>
      </Prose>

      {coverage.length > 0 && (
        <section className="block">
          <h2>Five risks, and which of them has executed evidence.</h2>
          <p className="deck">
            The field scores multi-agent risk in five categories and weights them
            towards the terminal harms. Those scores are estimates: a model reads a pair of
            descriptions and judges. This instrument replaces some of them with runs, and the
            honest report is not how many runs there are but what any of them is evidence
            for. {absent.length} of the {coverage.length} categories have none.
          </p>

          <div className="risks">
            {coverage.map((c) => (
              <div key={c.key} className="risk-row">
                <div className="rk-cell">
                  <span className="rk">{c.key}</span>
                  <span className={`state ${c.covered ? "done" : "warn"}`}>
                    {c.covered ? "executed" : "estimated only"}
                  </span>
                </div>
                <div className="risk">
                  <h3>{c.title}</h3>
                  <p>{c.definition}</p>
                  {c.covered ? (
                    <p className="note">
                      Executed here by{" "}
                      {c.scenarios.map((sc, i) => (
                        <span key={sc}>
                          {i > 0 ? " and " : ""}
                          <em>{scenarioInfo(sc).title}</em> ({runsFor(sc)} verdicts)
                        </span>
                      ))}
                      . Each confirms by a side effect a criterion checks, never by a model
                      reading a transcript.
                    </p>
                  ) : (
                    <p className="note absent">{c.why_absent}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <Prose>

        <h3 className="stop">Not covered, and not yet measured</h3>
        <p>
          Stated first, because a threat model read as a list of covered cases
          is a threat model that has misled someone.
        </p>
        <ul>
          <li>
            <strong>No agent has been invoked.</strong> Every figure published
            so far concerns whether a container builds and its environment
            starts. Nothing here is evidence about agent behaviour.
          </li>
          <li>
            <strong>No pair has been run.</strong> The adversarial scenarios are
            specified and the sandbox that executes them exists, but no two
            agents have yet shared a workspace under measurement here.
          </li>
          <li>
            <strong>The one paper published reports viability only.</strong> It
            concerns whether containers build and start, and states no result
            about agent behaviour or interaction.
          </li>
          <li>
            <strong>The agents measured are Python, and not all of them.</strong>
            The build recipe reads Python packaging. Agents written in other
            languages are recorded as unsupported rather than as failures, but
            they are absent from every rate on this site.
          </li>
          <li>
            <strong>Model behaviour is out of scope.</strong> Agents under test
            run against a small local model. Results are about how agents
            interact, not about how capable a model is.
          </li>
        </ul>

        <h3>In scope, once pairs run</h3>
        <ul>
          <li>One agent reading a secret placed only in another agent&rsquo;s environment.</li>
          <li>One agent acting on instructions another wrote into shared state.</li>
          <li>A narrow agent inducing a broader one to act beyond its own scope.</li>
          <li>Two agents failing to terminate against each other.</li>
          <li>Anything leaving the network allowlist.</li>
        </ul>

        <h3>How a result is established</h3>
        <p>
          Every scenario carries a mechanically checkable criterion, because a
          model that decides results is a model that can be wrong about them.
          A confirmed exfiltration is a planted token appearing verbatim in
          another agent&rsquo;s output, not a judgement about whether something
          looked like exfiltration. A model is consulted only where a
          transcript is genuinely ambiguous, and every verdict records whether
          a deterministic property, a tripwire, or a model established it.
        </p>
      </Prose>

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1.75rem; max-width: 22ch; }
        .stop { border-left: 2px solid var(--signal-stop); padding-left: 0.9rem; }
        .risks { display: flex; flex-direction: column; }
        .risk-row { display: grid; grid-template-columns: 9rem minmax(0, 1fr); column-gap: 2.5rem;
          border-top: var(--hair) solid var(--rule); padding: 1.2rem 0; }
        .rk-cell { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-start; }
        .rk { font-family: var(--font-display); font-size: 2.4rem; line-height: 1; color: var(--ink); }
        .risk { display: flex; flex-direction: column; gap: 0.55rem; min-width: 0; }
        .risk h3 { font-style: italic; }
        @media (max-width: 720px) { .risk-row { grid-template-columns: 1fr; row-gap: 0.7rem; } }
        .risk .absent { border-left: 2px solid var(--warn); padding-left: 0.9rem; }
      `}</style>
    </div>
  );
}
