import { instrumentStats, loadDataset, loadManifest } from "../../lib/dataset";
import { Telemetry } from "../../components/Telemetry";

export const metadata = { title: "Instrument | CRUCIBLE" };

function Bars({ counts, tone }: { counts: Record<string, number>; tone: Record<string, string> }) {
  const max = Math.max(1, ...Object.values(counts));
  const keys = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  return (
    <div className="stack" style={{ gap: "0.55rem" }}>
      {keys.map((k) => (
        <div key={k} style={{ display: "grid", gridTemplateColumns: "9rem 1fr 3ch", gap: "0.8rem", alignItems: "center", fontSize: "var(--t-small)" }}>
          <span className={`pill ${tone[k] ?? "inert"}`}>{k}</span>
          <div style={{ height: 6, background: "var(--ground-raised)", border: "var(--hair) solid var(--rule)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ width: `${(counts[k] / max) * 100}%`, height: "100%", background: "var(--rule-bright)" }} />
          </div>
          <span className="num">{counts[k]}</span>
        </div>
      ))}
    </div>
  );
}

export default function Instrument() {
  const data = loadDataset(); const m = loadManifest();
  const s = instrumentStats(data, m);
  const t = s.tables;
  return (
    <div className="sheet page stack">
      <div><p className="label">Instrument</p><h1>What is queued, blocked, artifact, earned</h1>
        <p className="lede">The state of the record itself, as of the last unattended research pass. The pass runs the arena, classifies every run from its own evidence, regenerates the papers, and republishes; this site rebuilds from what it published.</p></div>
      <Telemetry items={[
        { label: "Candidates", value: t.candidates ?? 0 },
        { label: "Builds", value: t.builds ?? 0 },
        { label: "Env checks", value: t.env_checks ?? 0, tone: "cool" },
        { label: "Entrypoints", value: t.entrypoints ?? 0 },
        { label: "Solo attempts", value: t.solos ?? 0 },
        { label: "Pair runs", value: t.pairs ?? 0, tone: "hot" },
      ]} />
      <div className="grid-2">
        <section className="panel"><div className="panel-head"><span className="title">Pair runs by status</span></div>
          <div className="panel-body"><Bars counts={s.pairsByStatus} tone={{ done: "ok", artifact: "artifact", blocked: "inert", lost: "stop" }} />
            <p className="note" style={{ marginTop: "0.9rem" }}>Only done enters a rate. Artifact means the verdict came from the instrument and not the agents; blocked means the sandbox refused to start them.</p></div></section>
        <section className="panel"><div className="panel-head"><span className="title">Solo attempts by outcome</span></div>
          <div className="panel-body"><Bars counts={s.solosByOutcome} tone={{ acted: "ok", ran_no_effect: "warn", failed: "stop" }} />
            <p className="note" style={{ marginTop: "0.9rem" }}>Every attempt is kept. The ones that ran and did nothing are the evidence that the entrypoints which act were earned rather than guessed.</p></div></section>
      </div>
      <div className="grid-2">
        <section className="panel"><div className="panel-head"><span className="title">Pinned variables</span></div>
          <dl className="kv panel-body">
            <dt>models</dt><dd>{s.models.map((x) => <code key={x} style={{ display: "block" }}>{x}</code>)}</dd>
            <dt>entrypoint authors</dt><dd>{s.authors.map((x) => <code key={x} style={{ display: "block" }}>{x}</code>)}</dd>
            <dt>engine commit</dt><dd><code>{m.engine_commit.slice(0, 12)}</code></dd>
            <dt>last record</dt><dd><code>{s.lastAt.slice(0, 19).replace("T", " ")}</code></dd>
          </dl></section>
        <section className="panel"><div className="panel-head"><span className="title">Research schedule</span>
            {m.research.last_pass ? <span className="pill ok live">running unattended</span> : <span className="pill inert">no pass yet</span>}</div>
          <dl className="kv panel-body">
            <dt>last pass</dt><dd><code>{m.research.last_pass ? m.research.last_pass.slice(0, 19).replace("T", " ") : "none recorded"}</code></dd>
            <dt>cadence</dt><dd>{m.research.cadence_hours ? <code>every {m.research.cadence_hours} hours while the machine is on</code> : <span className="note">not scheduled; passes are started by hand</span>}</dd>
            <dt>passes</dt><dd><code>{m.research.passes ?? 0}</code></dd>
            <dt>parameters</dt><dd>
              {m.research.params ? (
                <pre className="mono" style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "var(--t-micro)", color: "var(--ink-soft)" }}>{JSON.stringify(m.research.params, null, 2)}</pre>
              ) : <span className="note">published with the next pass</span>}
            </dd>
            <dt>to change them</dt><dd>edit <code>research.yaml</code> at the repository root and commit. Each pass pulls the repository before it starts, so a change made anywhere applies on the next pass: which scenarios, which agents pair, how many rounds, which seed lists to harvest, and how often. A new entrypoint committed to <code>entrypoints/</code> is verified by the solo gate on the next pass and enters the arena if it acts.</dd>
            <dt>what a pass does</dt><dd>every invocable pair against every adversarial scenario, each run classified from its transcript and property report by fixed rules, papers regenerated and verified, dataset republished, committed and pushed. A pass that changes nothing commits nothing.</dd>
            <dt>what it never does</dt><dd>choose which agents count, write an entrypoint, or call a run a verdict by any rule not in the classifier.</dd>
          </dl></section>
      </div>
    </div>
  );
}
