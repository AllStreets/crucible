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

| `FoundationAgents/OpenManus` | Builds on a 3.12 base, and cannot be configured or pointed at the shared workspace. It reads its model settings from `config/config.toml` inside the repository and roots every file it writes at `workspace/` beside that, both under an image root the sandbox mounts read only. There is no environment variable for either. Running it would mean writing into the image, and an agent whose files never reach the shared workspace cannot take part in a shared-workspace scenario at all. |

| `Significant-Gravitas/AutoGPT` | Builds on a 3.12 base with `cryptography` pinned, starts, takes its task on standard input, and reaches the model endpoint. It then refuses the model: `SMART_LLM` and `FAST_LLM` are validated against closed enumerations of known provider models, so a name that is not on its list is rejected before the first request. This project's model is a locally served constant, recorded on every row, and the only local name its enumerations accept belongs to a different model entirely. Using that name would falsify the one variable the whole dataset is pinned to, so the agent is recorded here. Everything up to the model call was observed working. |
| `SWE-agent/SWE-agent` | Builds and has a CLI, and an entrypoint was written and run three times. It refuses a workspace that is not a git repository; with one initialised, its local deployment copies the repository to a path at the filesystem root derived from the repository's name, which collides with the workspace itself and, under the arena's read-only root, could not be created regardless. Edits would land in that copy rather than the shared workspace. Adapting it further would be shaping the agent to the harness, so it is recorded here with what was tried. |
| `simonw/llm` | Builds and runs. It is a command-line interface to models rather than an agent: it acts on the world only through tools passed to it as Python functions the operator writes. An entrypoint that supplied a write-file function would be measuring a tool this project wrote, not the agent, so it is recorded here rather than invoked. |
| `Pythagora-io/gpt-pilot` | Builds, but is an interactive project builder: `main.py` drives a multi-step conversation backed by a database and expects a person at each step. `--initial-prompt` seeds it; nothing makes it complete a bounded task and exit. Not invocable non-interactively. |
| `FoundationAgents/MetaGPT` | Did not build. Pins `lancedb==0.4.0`, which no longer exists on the index. A dependency conflict, and a property of the repository at this commit. |
| `smol-ai/developer` | Did not build. `setup.py` fails during metadata generation at this commit; last pushed in 2024. |
| `OpenBMB/ChatDev` | Did not build. Metadata generation fails at the root manifest. |

Three agents were blocked on one thing, a base image newer than Python 3.11, and
that is now a variable a seed line declares and a build row records. All three
build. None of the three can yet be invoked, and the reasons are worth separating.

AutoGPT and OpenHands were both blocked by the same third-party wheel.
`cryptography` 50.0.1 crashes the interpreter with an illegal instruction when its
Rust extension is imported on this machine, at both Python versions tested, while
45.0.7 and 42.0.8 on the same base import cleanly. Neither agent did anything
wrong: each resolved the current release of a dependency it declares, and that
release is broken on this hardware. A seed line can now declare a version to force
after the agent's own resolution, and the build row records it, because a build
whose dependency set was overridden is a different measurement and a reader has to
see that it happened.

With the pin, OpenHands runs and is in the arena. AutoGPT gets further than before
and stops at its own model validation, which no pin reaches. OpenManus is blocked by
its own design rather than by a dependency, and no pin would have helped it.

Four of the ten first agents build and install cleanly but cannot be invoked to perform a
task. Three of those four are frameworks that agents are built with rather than
agents that run, which is the distinction the submit page asks proposers to
observe and is easy to lose when counting stars.
