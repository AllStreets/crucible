import Link from "next/link";
import { loadDataset, loadManifest, repoNames } from "../../lib/dataset";
import { ParameterDesk, type DeskParams } from "../../components/ParameterDesk";
import { Prose } from "../../components/Prose";

export const metadata = { title: "Control | Crucible" };

const FALLBACK: DeskParams = {
  model: "", ollama: "", scenarios: [], agents: "all-invocable",
  rounds: 1, seeds: [], cadence_hours: 6, pull: true,
};

export default function Control() {
  const data = loadDataset();
  const m = loadManifest();
  const names = repoNames(data);
  const params = { ...FALLBACK, ...(m.research?.params as Partial<DeskParams> ?? {}) } as DeskParams;
  const invocable = [...new Set(data.solos.filter((s) => s.outcome === "acted").map((s) => s.slug))].sort();
  const allScenarios = [...new Set([...data.pairs.map((p) => p.scenario), ...params.scenarios])].sort();
  const unattended = (m.research?.unattended_passes ?? 0) > 0;

  return (
    <div className="sheet page stack">
      <div>
        <div className="eyebrow"><span className="label">Control</span></div>
        <h1>Set what the next pass runs.</h1>
        <p className="lede">
          Every pass begins by pulling this repository and reading one file, so that file is the
          control plane. Change it, commit it, and the scheduler runs the new experiment on its
          next firing, classifies each run from its transcript, regenerates the papers, and
          publishes the result here. Nobody starts anything.
        </p>
      </div>

      <div className="telemetry">
        <div>
          <span className={`state ${unattended ? "hot live" : "active"}`}>
            {unattended ? "running unattended" : "runs when started"}
          </span>
          <span className="sub">scheduler</span>
        </div>
        <div>
          <span className="val">{m.research?.passes ?? 0}</span>
          <span className="sub">passes recorded</span>
        </div>
        <div>
          <span className="val">{m.research?.cadence_hours ?? 0}</span>
          <span className="sub">hours between passes</span>
        </div>
        <div>
          <span className="val">{invocable.length}</span>
          <span className="sub">agents that can be invoked</span>
        </div>
      </div>

      <ParameterDesk current={params} allScenarios={allScenarios} invocable={invocable} names={names} />

      <section className="block">
        <h2>Why this page has no apply button.</h2>
        <Prose>
          <p>
            It could have one. It would need a server that accepts instructions from the
            internet and runs containers on a machine holding this dataset, which is a worse
            idea than any experiment it could schedule. The gate on what this instrument runs is
            commit access to the repository, and that is a real gate rather than a page with a
            button hidden from the wrong people.
          </p>
          <p>
            So the desk above writes the file exactly, starting from the parameters currently in
            force. Commit it and the next pass is the new experiment. Nothing else needs doing:
            a new entrypoint committed alongside it is solo-gated on the same pass and enters the
            arena if it acts, and the papers and this site are regenerated from the records the
            pass produced.
          </p>
          <p>
            What a pass will never do is choose which agents count, write an entrypoint, or call
            a run a verdict by any rule that is not in the classifier. Those are decisions, and
            decisions have authors. <Link href="/instrument/">What a pass does, step by step.</Link>
          </p>
        </Prose>
      </section>
    </div>
  );
}
