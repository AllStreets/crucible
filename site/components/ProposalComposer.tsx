"use client";

import { useMemo, useState } from "react";

/** Builds a research proposal and hands it to the issue tracker.
 *
 *  The form is the point rather than decoration: a proposal that names its
 *  agents, its criterion and its failing case is one a pass can run, and a
 *  proposal that names none of them is a wish. The fields are the questions a
 *  person would otherwise have to be asked in a thread. Nothing is posted from
 *  here; the composed text goes to the issue tracker, where it is public and
 *  has an author.
 */
const SCENARIO_TITLES: Record<string, string> = {
  induced_execution: "Induced execution",
  partner_escalation: "Partner escalation",
  secret_exfiltration: "Secret exfiltration",
  state_poisoning: "State poisoning",
};

export function ProposalComposer(
  { agents, names, scenarios }: { agents: string[]; names: Record<string, string>; scenarios: string[] },
) {
  const [question, setQuestion] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [scenario, setScenario] = useState<string>(scenarios[0] ?? "");
  const [criterion, setCriterion] = useState("");
  const [wrong, setWrong] = useState("");
  const [copied, setCopied] = useState(false);

  const short = (s: string) => names[s] ?? s;
  const toggle = (slug: string) =>
    setPicked((p) => (p.includes(slug) ? p.filter((x) => x !== slug) : [...p, slug]));

  const body = useMemo(() => [
    "## The question",
    question.trim() || "_(what should this instrument find out)_",
    "",
    "## Agents to put in the room",
    picked.length ? picked.map((p) => `- ${p}`).join("\n")
      : "_(any that can be invoked, or name one that cannot and this becomes a request for an entrypoint)_",
    "",
    "## Scenario",
    scenario ? `${SCENARIO_TITLES[scenario] ?? scenario} (\`${scenario}\`)` : "_(new scenario)_",
    "",
    "## What would count as an answer",
    criterion.trim() || "_(a side effect a machine can check, not a judgement about a transcript)_",
    "",
    "## What would mean the instrument is wrong",
    wrong.trim() || "_(the result that would make me distrust this run)_",
    "",
    "---",
    "Composed on the propose page. Nothing was submitted anywhere else.",
  ].join("\n"), [question, picked, scenario, criterion, wrong]);

  const url = "https://github.com/AllStreets/crucible/issues/new?labels=research-proposal&title="
    + encodeURIComponent(question.trim() ? `Research: ${question.trim().slice(0, 70)}` : "Research proposal")
    + "&body=" + encodeURIComponent(body);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(body);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { setCopied(false); }
  };

  return (
    <section className="composer">
      <label className="field">
        <span className="label">The question</span>
        <textarea rows={2} value={question} onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Does an agent that asks before running a command resist induced execution?" />
      </label>

      <fieldset className="field">
        <legend className="label">Agents to put in the room</legend>
        <div className="chips">
          {agents.map((a) => (
            <button key={a} type="button" className={picked.includes(a) ? "on" : ""}
                    onClick={() => toggle(a)} aria-pressed={picked.includes(a)}>
              {short(a)}
            </button>
          ))}
        </div>
        <p className="hint">
          These are the agents that can currently be invoked. Naming one that cannot turns this
          into a request for an entrypoint, which is the scarcer contribution.
        </p>
      </fieldset>

      <label className="field">
        <span className="label">Scenario</span>
        <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
          {scenarios.map((s) => <option key={s} value={s}>{SCENARIO_TITLES[s] ?? s}</option>)}
          <option value="">something that does not exist yet</option>
        </select>
      </label>

      <label className="field">
        <span className="label">What would count as an answer</span>
        <textarea rows={2} value={criterion} onChange={(e) => setCriterion(e.target.value)}
                  placeholder="A file at a known path that only running the planted script creates." />
      </label>

      <label className="field">
        <span className="label">What would mean the instrument is wrong</span>
        <textarea rows={2} value={wrong} onChange={(e) => setWrong(e.target.value)}
                  placeholder="The marker exists but the victim never read the planted file." />
      </label>

      <div className="actions">
        <a className="btn primary" href={url} target="_blank" rel="noreferrer">Open it as an issue</a>
        <button type="button" className="btn" onClick={copy}>
          {copied ? "Copied" : "Copy the text"}
        </button>
      </div>

      <details className="preview">
        <summary>What gets composed</summary>
        <pre>{body}</pre>
      </details>

      <style>{`
        .composer { display: flex; flex-direction: column; gap: 1.6rem;
          border-top: var(--hair) solid var(--rule-strong); padding-top: 1.6rem; }
        .field { display: flex; flex-direction: column; gap: 0.5rem; border: 0; padding: 0; margin: 0; }
        .field textarea, .field select { max-width: 62ch; }
        .hint { font-size: var(--t-small); color: var(--ink-soft); max-width: 62ch; }
        .chips { display: flex; flex-wrap: wrap; gap: 0.45rem; }
        .chips button { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-soft);
          background: transparent; border: var(--hair) solid var(--rule); padding: 0.38rem 0.75rem;
          cursor: pointer; }
        .chips button:hover { color: var(--ink); border-color: var(--rule-strong); }
        .chips button.on { color: var(--ground); background: var(--earned); border-color: var(--earned); }
        .actions { display: flex; flex-wrap: wrap; gap: 0.8rem; }
        .actions .btn { cursor: pointer; font-size: var(--t-body); }
        .preview summary { font-size: var(--t-small); color: var(--ink-soft); cursor: pointer; }
        .preview pre { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-soft);
          white-space: pre-wrap; background: var(--panel); border: var(--hair) solid var(--rule);
          padding: 1rem; margin-top: 0.7rem; overflow-x: auto; }
      `}</style>
    </section>
  );
}
