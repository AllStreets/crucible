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

  const short = (s: string) => names[s] ?? s;
  const toggle = (list: string[], set: (v: string[]) => void, v: string) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const chosenAgents = everyAgent ? invocable : agents;
  const pairs = chosenAgents.length * Math.max(0, chosenAgents.length - 1);
  const runsPerPass = pairs * scenarios.length * Math.max(1, rounds);

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
  ].join("\n"), [model, scenarios, everyAgent, agents, rounds, cadence, current]);

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
        .desk input { font-family: var(--font-mono); font-size: var(--t-body); color: var(--ink);
          background: var(--panel); border: var(--hair) solid var(--rule); padding: 0.6rem 0.7rem;
          max-width: 34ch; }
        .desk input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
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
