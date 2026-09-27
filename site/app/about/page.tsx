import { Prose } from "../../components/Prose";

export const metadata = { title: "About | Crucible" };

export default function About() {
  return (
    <div className="sheet page">
      <div className="eyebrow"><span className="label">About</span></div>
      <h1>An instrument, not an argument</h1>
      <Prose>
        <p>
          You install a coding agent. Then a notes agent. Then something for
          your calendar. They share your filesystem, your clipboard, your OAuth
          scopes, your MCP servers, your wallet. Nobody has systematically
          studied what happens when they interact.
        </p>
        <p>
          CRUCIBLE clones real agents from GitHub, pins their commit SHAs,
          builds them into containers, checks whether those containers start,
          and publishes the distribution of why the rest do not. Later phases
          run working pairs against each other under adversarial scenarios with
          deterministic criteria.
        </p>
        <p className="pull">
          An estimate of a risk is an opinion about it. This runs the
          experiment.
        </p>
        <h3>Built on SMADP, not forked from it</h3>
        <p>
          SMADP published the estimated matrix of multi-agent risk and the
          sandbox that can execute it. CRUCIBLE imports that sandbox as a
          library and contributes the half that was missing: getting real agents
          to the starting line in volume.
        </p>
        <h3>Source</h3>
        <p>
          The engine, this site, every spec and every run record live in one
          repository. The specs include the arguments that were rejected and
          why, which is usually the more useful half.
        </p>
      </Prose>
      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1.75rem; max-width: 22ch; }
        .pull {
          font-family: var(--font-display);
          font-size: var(--t-h3);
          font-style: italic;
          border-left: 2px solid var(--accent);
          padding-left: 1.1rem;
          margin: 0.5rem 0;
        }
      `}</style>
    </div>
  );
}
