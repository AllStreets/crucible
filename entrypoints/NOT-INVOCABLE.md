# Agents with no entrypoint, and why

Recorded rather than omitted. An agent absent from the arena with no stated
reason is indistinguishable from an agent nobody got round to, and the count of
agents that cannot be invoked is a finding in its own right.

| Agent | Why no entrypoint exists |
|---|---|
| `openai/swarm` | A library. Ships `swarm` as an importable package with examples, and no console script. Running it requires writing a driver, and a driver written here would be the thing measured, not the agent. |
| `langchain-ai/langgraph` | A library, same shape as swarm. Installs and imports; exposes no runnable agent. |
| `yoheinakajima/babyagi` | A Flask dashboard. `main.py` calls `create_app('/dashboard')` and serves a web UI on port 8080. The current project is a function framework, not the original autonomous task loop, and it performs no task from a command line. |
| `browser-use/browser-use` | Needs a browser this harness does not install. `browser-use doctor` in the built image reports chrome not running, daemon not alive, zero browser connections. The CLI drives an external Chromium over CDP. This is a limit of the harness, not a defect of the agent. |
| `microsoft/autogen` | Did not build. Workspace root, not an installable package. |
| `crewAIInc/crewAI` | Did not build. Workspace root whose install produced a distribution named UNKNOWN. |
| `continuedev/continue` | Did not build. TypeScript, which this recipe does not read. |
| `anomalyco/opencode` | Did not build. TypeScript, same. |

Four of the ten build and install cleanly but cannot be invoked to perform a
task. Three of those four are frameworks that agents are built with rather than
agents that run, which is the distinction the submit page asks proposers to
observe and is easy to lose when counting stars.
