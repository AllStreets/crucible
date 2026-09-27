import { Prose } from "../../components/Prose";

export const metadata = { title: "Threat model | Crucible" };

export default function ThreatModel() {
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
      `}</style>
    </div>
  );
}
