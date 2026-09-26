import { Prose } from "../../components/Prose";

export const metadata = { title: "Submit | CRUCIBLE" };

const ISSUE_URL =
  "https://github.com/AllStreets/crucible/issues/new?title=Agent%20proposal&body=" +
  encodeURIComponent(
    "Repository URL:\n\nWhy this agent is one people actually run:\n\n" +
    "What it shares with other agents (filesystem, shell, network, credentials):\n\n" +
    "Known invocation, if you have one:\n",
  );

export default function Submit() {
  return (
    <div className="sheet page">
      <p className="label">Submit</p>
      <h1>Propose an agent</h1>
      <Prose>
        <p>
          The seed list is chosen by hand rather than by ranking, because the
          figures on this site are claims about agents people actually run. A
          list assembled by stars would measure popularity instead, and nothing
          would error.
        </p>
        <p>
          So proposals arrive as issues and a person decides. This page posts
          nothing, collects nothing and stores nothing: there is no form
          handler and no endpoint, because a static site that gathered
          submissions would need both.
        </p>
        <p className="cta">
          <a href={ISSUE_URL} rel="noreferrer">Open a proposal issue</a>
        </p>
        <h3>What makes a good proposal</h3>
        <ul>
          <li>An agent that runs, rather than a library agents are built with.</li>
          <li>Evidence that people run it alongside other agents.</li>
          <li>An invocation you have actually used, if you have one. That is the scarcest thing here.</li>
        </ul>
      </Prose>
      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1.75rem; max-width: 22ch; }
        .cta a {
          display: inline-block;
          font-family: var(--font-mono);
          font-size: var(--t-small);
          letter-spacing: 0.06em;
          text-transform: uppercase;
          text-decoration: none;
          border: var(--rule-hair) solid var(--ink);
          padding: 0.7rem 1.2rem;
        }
        .cta a:hover { background: var(--ink); color: var(--ground); }
      `}</style>
    </div>
  );
}
