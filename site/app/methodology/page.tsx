import { Figure, Prose } from "../../components/Prose";

export const metadata = { title: "Method | Crucible" };

export default function Methodology() {
  return (
    <div className="sheet page">
      <div className="eyebrow"><span className="label">Method</span></div>
      <h1>How a run works, and what it does not claim</h1>

      <Prose>
        <p>
          A run takes a seed list of repository URLs and carries each one
          through four recorded stages. Every stage writes a row whether it
          succeeds or fails, and a failure is a result rather than a blocked
          task. Nothing is skipped in silence.
        </p>

        <Figure n={1} caption="The four stages. Each writes a row, including on success, because a success with no stored evidence cannot be audited later.">
          <pre className="mono stage">{`harvest     resolve each repository to a commit SHA
forge       build a container at that pinned commit
env check   start the image with egress denied, run a probe
report      count rows, and name what was not measured`}</pre>
        </Figure>

        <h3>What the environment check measures</h3>
        <p>
          The check starts the built image and runs the probe the recipe
          installs: the interpreter comes up, prints one line, exits. That is
          the whole of it. The container command overrides whatever entrypoint
          the agent has, so a passing check means the environment works, not
          that the agent does.
        </p>
        <p>
          An earlier draft of this project called that stage a boot. It was not
          one. The agents measured here share no entrypoint, and with no
          network and no credentials an invocation would measure the harness
          rather than the agent, contaminating the exact distribution this
          exists to report. Verifying that an agent itself runs needs a
          hand-written entrypoint per agent and has not been done.
        </p>

        <h3>What is pinned, and why</h3>
        <p>
          Every build row records the commit SHA, the image ID, and a sha256 of
          the build recipe. The recipe is an experimental variable: it decides
          which agents are buildable at all, so rows produced under two versions
          of it are two measurements and pooling them would not be one. That
          column exists because changing the recipe once would otherwise have
          silently redefined every figure already published.
        </p>

        <h3>Where the model sits</h3>
        <p>
          Agents under test talk to a local model endpoint through the
          OpenAI-compatible interface, so the model is an experimental constant
          rather than someone else&rsquo;s drifting dependency. The model name
          and base URL are recorded on every check, since the same image checked
          against a different endpoint is a different measurement.
        </p>

        <h3>What a correction looks like</h3>
        <p>
          Records are append-only. The store has no update method and a test
          asserts its absence. A correction is a new row plus a supersedes row,
          and both stay readable; superseded rows are excluded from every
          published count through a single shared definition, so a figure on
          this site and a figure in a report cannot disagree.
        </p>
      </Prose>

      <style>{`
        .page { padding: 3.5rem 0 1rem; }
        .page h1 { margin: 0.7rem 0 1.75rem; max-width: 22ch; }
        .stage { font-size: var(--t-small); line-height: 1.8; margin: 0; white-space: pre; }
      `}</style>
    </div>
  );
}
