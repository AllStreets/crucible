import Link from "next/link";
import { loadDataset, loadManifest, repoNames } from "../../lib/dataset";
import { Prose } from "../../components/Prose";
import { ProposalComposer } from "../../components/ProposalComposer";

export const metadata = { title: "Propose research | Crucible" };

export default function Propose() {
  const data = loadDataset();
  const m = loadManifest();
  const names = repoNames(data);
  const invocable = data.solos
    .filter((s) => s.outcome === "acted")
    .map((s) => s.slug)
    .filter((v, i, a) => a.indexOf(v) === i)
    .sort();
  const scenarios = [...new Set(data.pairs.map((p) => p.scenario))].sort();

  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Propose research</span></div>
        <h1>Ask this instrument a question.</h1>
        <p className="lede">
          The arena runs unattended on a schedule, and what it runs is a file in a repository.
          A proposal that names a question, the agents to put in the room, and what would count
          as an answer can become the next pass. This page composes that proposal; it posts
          nothing and stores nothing, because a static site that collected submissions would
          need a server and this one deliberately has none.
        </p>
      </div>

      <ProposalComposer agents={invocable} names={names} scenarios={scenarios} />

      <section className="block">
        <h2>What makes a proposal runnable.</h2>
        <Prose>
          <p>
            The hard part is never the question. It is stating, in advance, what result would
            count as an answer and what result would mean the instrument was wrong, because a
            question with no failing case produces a number nobody can argue with and nobody
            should believe.
          </p>
          <ul>
            <li>
              <b>A criterion a machine can check.</b> Every scenario here confirms by side
              effect: a file that only executing the planted instruction creates, a canary that
              appears in the attacker&apos;s own output. A proposal whose answer depends on a
              model reading a transcript and deciding is a proposal for an opinion.
            </li>
            <li>
              <b>Agents that can be invoked.</b> {invocable.length} of the{" "}
              {m.counts.candidates} harvested can be. The rest are recorded in the repository
              with the reason, and a proposal naming one of them becomes a request for an
              entrypoint instead, which is slower and more valuable.
            </li>
            <li>
              <b>A result you would publish either way.</b> The most common outcome here is
              that nothing happens, and that is the finding roughly two thirds of the time.
            </li>
          </ul>
          <p>
            Proposals arrive as issues and a person decides. <Link href="/submit/">Proposing an
            agent</Link> rather than a question is a separate and equally useful thing.
          </p>
        </Prose>
      </section>
    </div>
  );
}
