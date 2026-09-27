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
        <p className="lede">The state of the record itself. There is no scheduler: runs are launched by a person and the site reads what they left behind, so this page is a heartbeat of the dataset rather than of a process.</p></div>
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
        <section className="panel"><div className="panel-head"><span className="title">Not running</span></div>
          <div className="panel-body note stack" style={{ gap: "0.6rem" }}>
            <p>No scheduler, no queue worker, no cloud runner. A run happens when a person starts one against a local model and a local daemon.</p>
            <p>That is stated here so the counts above are read as a record of what was done, not as a rate at which things happen.</p>
          </div></section>
      </div>
    </div>
  );
}
