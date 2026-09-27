import { DefectTimeline } from "../../components/DefectTimeline";
import { LOG } from "../../lib/log";

export const metadata = { title: "Log | Crucible" };

export default function LogPage() {
  const retractions = LOG.filter((e) => e.kind === "retraction").length;
  return (
    <div className="sheet page stack">
      <div><p className="label">Research log</p><h1>What changed, and what was withdrawn</h1>
        <p className="lede">Retractions stay here rather than being deleted. A withdrawn claim that vanishes leaves a reader unable to tell whether it was ever made.</p>
        <div style={{ display: "flex", gap: "0.6rem" }}><span className="pill inert">{LOG.length} entries</span><span className="pill stop">{retractions} retractions</span></div></div>
      <section className="panel"><div className="panel-body"><DefectTimeline /></div></section>
    </div>
  );
}
