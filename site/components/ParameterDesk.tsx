"use client";

import { useMemo, useState } from "react";

/** Compose the parameters of the next unattended pass.
 *
 *  What this page can honestly be is decided by what the instrument actually
 *  is. Every pass begins by pulling the repository and reading research.yaml,
 *  so that file is the control plane: change it, commit it, and the next pass
 *  runs the new thing without anyone starting anything. This desk writes that
 *  file exactly, from the parameters the engine accepts, starting from the
 *  ones currently in force.
 *
 *  It does not apply them, and it does not pretend to. A static page with an
 *  Apply button would need a server that takes instructions from the internet
 *  and runs containers, which is a worse idea than any research it could
 *  schedule. The gate is commit access, which is a real gate rather than a
 *  page that hides a button.
 */
const SCENARIO_TITLES: Record<string, string> = {
  induced_execution: "Induced execution",
  partner_escalation: "Partner escalation",
  secret_exfiltration: "Secret exfiltration",
  state_poisoning: "State poisoning",
};

export interface DeskParams {
  model: string;
  ollama: string;
  scenarios: string[];
  agents: string | string[];
  rounds: number;
  seeds: string[];
  cadence_hours: number | null;
  pull: boolean;
}

export function ParameterDesk(
  { current, allScenarios, invocable, names }:
  { current: DeskParams; allScenarios: string[]; invocable: string[]; names: Record<string, string> },
) {
  const [scenarios, setScenarios] = useState<string[]>(current.scenarios);
  const [everyAgent, setEveryAgent] = useState(!Array.isArray(current.agents));
  const [agents, setAgents] = useState<string[]>(
    Array.isArray(current.agents) ? current.agents : invocable);
  const [rounds, setRounds] = useState(current.rounds);
  const [cadence, setCadence] = useState<number>(current.cadence_hours ?? 6);
  const [model, setModel] = useState(current.model);
  const [copied, setCopied] = useState(false);

  // The experiment, optional. Without one a pass is a sweep; with one it runs
  // only what the question needs and reports against what was asked.
  const [question, setQuestion] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [vary, setVary] = useState<"" | "victim" | "attacker" | "scenario">("");
  const [holdScenario, setHoldScenario] = useState("");
  const [holdAttacker, setHoldAttacker] = useState("");
  const [repeats, setRepeats] = useState(1);
  const [comply, setComply] = useState<string[]>([]);
  const [hold, setHold] = useState<string[]>([]);

  const short = (s: string) => names[s] ?? s;
  const toggle = (list: string[], set: (v: string[]) => void, v: string) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const chosenAgents = everyAgent ? invocable : agents;
  const pairs = chosenAgents.length * Math.max(0, chosenAgents.length - 1);
  const runsPerPass = pairs * scenarios.length * Math.max(1, rounds);

  // An agent cannot be predicted to do both, because a prediction that cannot
  // be wrong is not a prediction.
  const toggleComply = (a: string) => {
    setComply((p) => (p.includes(a) ? p.filter((x) => x !== a) : [...p, a]));
    setHold((p) => p.filter((x) => x !== a));
  };
  const toggleHold = (a: string) => {
    setHold((p) => (p.includes(a) ? p.filter((x) => x !== a) : [...p, a]));
    setComply((p) => p.filter((x) => x !== a));
  };

  const yaml = useMemo(() => [
    "# The parameters of every unattended pass. Each pass pulls this file",
    "# before it starts, so a change committed here is the next experiment.",
    `model: ${model}`,
    `ollama: ${current.ollama}`,
    "scenarios:",
    ...(scenarios.length ? scenarios.map((s) => `  - ${s}`) : ["  []"]),
    everyAgent ? "agents: all-invocable" : "agents:",
    ...(everyAgent ? [] : agents.map((a) => `  - ${a}`)),
    `rounds: ${rounds}`,
    "seeds:" + (current.seeds.length ? "" : " []"),
    ...current.seeds.map((s) => `  - ${s}`),
    `cadence_hours: ${cadence}`,
    `pull: ${current.pull}`,
    ...(question || vary ? [
      "",
      "experiment:",
      ...(question ? ["  question: >", `    ${question}`] : []),
      ...(hypothesis ? ["  hypothesis: >", `    ${hypothesis}`] : []),
      ...(vary ? [`  vary: ${vary}`] : []),
      ...(holdScenario || holdAttacker ? ["  holding:"] : []),
      ...(holdScenario ? [`    scenario: ${holdScenario}`] : []),
      ...(holdAttacker ? [`    attacker: ${holdAttacker}`] : []),
      ...(repeats > 1 ? [`  repeats: ${repeats}`] : []),
      ...(comply.length || hold.length ? ["  predict:"] : []),
      ...(comply.length ? [`    comply: [${comply.join(", ")}]`] : []),
      ...(hold.length ? [`    hold: [${hold.join(", ")}]`] : []),
    ] : []),
  ].join("\n"), [model, scenarios, everyAgent, agents, rounds, cadence, current,
                 question, hypothesis, vary, holdScenario, holdAttacker, repeats,
                 comply, hold]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { setCopied(false); }
  };

  return (
    <section className="desk">
      <div className="grid-2">
        <fieldset className="field">
          <legend className="label">Scenarios each pass runs</legend>
          <div className="chips">
            {allScenarios.map((s) => (
              <button key={s} type="button" className={scenarios.includes(s) ? "on" : ""}
                      aria-pressed={scenarios.includes(s)}
                      onClick={() => toggle(scenarios, setScenarios, s)}>
                {SCENARIO_TITLES[s] ?? s}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="field">
          <legend className="label">Agents</legend>
          <div className="chips">
            <button type="button" className={everyAgent ? "on" : ""} aria-pressed={everyAgent}
                    onClick={() => setEveryAgent(true)}>
              every invocable agent
            </button>
            <button type="button" className={!everyAgent ? "on" : ""} aria-pressed={!everyAgent}
                    onClick={() => setEveryAgent(false)}>
              a named set
            </button>
          </div>
          {!everyAgent && (
            <div className="chips second">
              {invocable.map((a) => (
                <button key={a} type="button" className={agents.includes(a) ? "on" : ""}
                        aria-pressed={agents.includes(a)}
                        onClick={() => toggle(agents, setAgents, a)}>
                  {short(a)}
                </button>
              ))}
            </div>
          )}
          <p className="hint">
            Choosing every invocable agent means a new entrypoint enters the arena on the pass
            after it is committed, without anyone editing this again.
          </p>
        </fieldset>

        <label className="field">
          <span className="label">Rounds per pass</span>
          <input type="number" min={1} max={20} value={rounds}
                 onChange={(e) => setRounds(Math.max(1, Number(e.target.value) || 1))} />
          <p className="hint">Each round runs every ordered pairing against every scenario again.</p>
        </label>

        <label className="field">
          <span className="label">Hours between passes</span>
          <input type="number" min={1} max={168} value={cadence}
                 onChange={(e) => setCadence(Math.max(1, Number(e.target.value) || 1))} />
          <p className="hint">The scheduler fires on this interval while the machine is awake.</p>
        </label>

        <label className="field">
          <span className="label">Model under the agents</span>
          <input type="text" value={model} onChange={(e) => setModel(e.target.value)} />
          <p className="hint">
            Pinned on every row. Changing it makes the rows that follow a different measurement
            from the rows before, which is why it is recorded rather than assumed.
          </p>
        </label>
      </div>

      <div className="estimate">
        <span className="figure small">{runsPerPass}</span>
        <p>
          runs per pass, from {chosenAgents.length} agents in {pairs} ordered pairings across{" "}
          {scenarios.length} scenarios. Both orderings of each pair run, because attacker and
          victim are different jobs.
        </p>
      </div>

      <section className="experiment">
        <div className="exp-head">
          <span className="label">An experiment, optional</span>
          <span className="note">
            Without one, a pass sweeps every ordering of every pair. With one, it runs only
            what the question needs and its report answers against what was asked.
          </span>
        </div>

        <label className="field">
          <span className="label">The question</span>
          <textarea rows={2} value={question} onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Does an agent that asks before running a command resist induced execution?" />
        </label>

        <label className="field">
          <span className="label">The hypothesis, stated in advance</span>
          <textarea rows={2} value={hypothesis} onChange={(e) => setHypothesis(e.target.value)}
                    placeholder="Agents whose invocation runs shell commands without confirmation comply; the rest hold." />
          <p className="hint">
            Carried verbatim into the report and evaluated by nothing. No model reads it and no
            rule scores it, because a tool that graded its own hypothesis would be the one thing
            this instrument must not be.
          </p>
        </label>

        <fieldset className="field">
          <legend className="label">Hold everything, vary one thing</legend>
          <div className="chips">
            {(["", "victim", "attacker", "scenario"] as const).map((v) => (
              <button key={v || "none"} type="button" className={vary === v ? "on" : ""}
                      aria-pressed={vary === v} onClick={() => setVary(v)}>
                {v === "" ? "no axis, sweep everything" : `vary the ${v}`}
              </button>
            ))}
          </div>
          {vary && (
            <div className="holding">
              <label>
                <span className="label">hold scenario</span>
                <select value={holdScenario} onChange={(e) => setHoldScenario(e.target.value)}
                        disabled={vary === "scenario"}>
                  <option value="">sweep all</option>
                  {allScenarios.map((s2) => <option key={s2} value={s2}>{SCENARIO_TITLES[s2] ?? s2}</option>)}
                </select>
              </label>
              <label>
                <span className="label">hold attacker</span>
                <select value={holdAttacker} onChange={(e) => setHoldAttacker(e.target.value)}
                        disabled={vary === "attacker"}>
                  <option value="">sweep all</option>
                  {invocable.map((a) => <option key={a} value={a}>{short(a)}</option>)}
                </select>
              </label>
              <label>
                <span className="label">runs per cell</span>
                <input type="number" min={1} max={20} value={repeats}
                       onChange={(e) => setRepeats(Math.max(1, Number(e.target.value) || 1))} />
              </label>
            </div>
          )}
          <p className="hint">
            A split one run wide could be noise. More runs per cell is the only honest way to
            tell the difference.
          </p>
        </fieldset>

        <fieldset className="field">
          <legend className="label">Predict, and be wrong in public</legend>
          <p className="hint">
            The only part that is scored, because naming an agent and what it should do is a
            claim rows can settle. An agent cannot be put in both lists.
          </p>
          <div className="predict">
            <div>
              <span className="label">expected to comply</span>
              <div className="chips">
                {invocable.map((a) => (
                  <button key={a} type="button" className={comply.includes(a) ? "on hot" : ""}
                          aria-pressed={comply.includes(a)} onClick={() => toggleComply(a)}>
                    {short(a)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <span className="label">expected to hold</span>
              <div className="chips">
                {invocable.map((a) => (
                  <button key={a} type="button" className={hold.includes(a) ? "on" : ""}
                          aria-pressed={hold.includes(a)} onClick={() => toggleHold(a)}>
                    {short(a)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </fieldset>
      </section>

      <div className="emit">
        <div className="emit-head">
          <span className="label">research.yaml</span>
          <button type="button" className="btn" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
        </div>
        <pre>{yaml}</pre>
      </div>

      <style>{`
        .desk { display: flex; flex-direction: column; gap: 1.8rem;
          border-top: var(--hair) solid var(--rule-strong); padding-top: 1.6rem; }
        .desk .field { display: flex; flex-direction: column; gap: 0.5rem; border: 0; padding: 0; margin: 0; }
        .desk input { font-family: var(--font-mono); max-width: 34ch; }
        .chips { display: flex; flex-wrap: wrap; gap: 0.45rem; }
        .chips.second { margin-top: 0.5rem; }
        .chips button { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-soft);
          background: transparent; border: var(--hair) solid var(--rule); padding: 0.38rem 0.75rem;
          cursor: pointer; }
        .chips button:hover { color: var(--ink); border-color: var(--rule-strong); }
        .chips button.on { color: var(--ground); background: var(--earned); border-color: var(--earned); }
        .hint { font-size: var(--t-small); color: var(--ink-soft); max-width: 52ch; }
        .estimate { display: flex; align-items: baseline; gap: 1.2rem;
          border-top: var(--hair) solid var(--rule); padding-top: 1.1rem; }
        .estimate .figure { font-family: var(--font-display); font-size: 3.2rem; line-height: 1;
          color: var(--accent); }
        .estimate p { font-size: var(--t-small); color: var(--ink-soft); max-width: 54ch; }
        .experiment { display: flex; flex-direction: column; gap: 1.4rem;
          border-top: var(--hair) solid var(--rule-strong); padding-top: 1.4rem; }
        .exp-head { display: flex; flex-direction: column; gap: 0.4rem; }
        .holding { display: flex; flex-wrap: wrap; gap: 1rem 1.6rem; margin-top: 0.6rem; }
        .holding label { display: flex; flex-direction: column; gap: 0.35rem; }
        .holding select, .holding input { font-family: var(--font-mono); font-size: var(--t-small);
          padding: 0.35rem 0.5rem; }
        .predict { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
          gap: 1.2rem 2rem; margin-top: 0.5rem; }
        .predict > div { display: flex; flex-direction: column; gap: 0.45rem; min-width: 0; }
        .chips button.on.hot { background: var(--accent); border-color: var(--accent); }
        .emit-head { display: flex; justify-content: space-between; align-items: center;
          border-top: var(--hair) solid var(--rule-strong); padding: 0.9rem 0 0.6rem; }
        .emit .btn { cursor: pointer; }
        .emit pre { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink);
          background: var(--panel); border: var(--hair) solid var(--rule); padding: 1rem;
          overflow-x: auto; margin: 0; }
      `}</style>
    </section>
  );
}
