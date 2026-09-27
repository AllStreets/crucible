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
| `OpenHands/OpenHands` | Builds on a 3.12 base, measured at 0.62.0, the last release before the project became an Electron application. It has a headless entry point and a CLI runtime that needs no Docker inside Docker, and it never reaches either: importing its own configuration module kills the interpreter with an illegal instruction. The cause is `cryptography` 50.0.1, a transitive dependency whose aarch64 wheel executes an instruction this machine does not implement. See the note below. |

| `Significant-Gravitas/AutoGPT` | Builds on a 3.12 base, having previously been recorded as requiring a Python the base image did not provide. Its `autogpt` command dies on start with an illegal instruction, from the same `cryptography` wheel that stops OpenHands. |
| `SWE-agent/SWE-agent` | Builds and has a CLI, and an entrypoint was written and run three times. It refuses a workspace that is not a git repository; with one initialised, its local deployment copies the repository to a path at the filesystem root derived from the repository's name, which collides with the workspace itself and, under the arena's read-only root, could not be created regardless. Edits would land in that copy rather than the shared workspace. Adapting it further would be shaping the agent to the harness, so it is recorded here with what was tried. |
| `simonw/llm` | Builds and runs. It is a command-line interface to models rather than an agent: it acts on the world only through tools passed to it as Python functions the operator writes. An entrypoint that supplied a write-file function would be measuring a tool this project wrote, not the agent, so it is recorded here rather than invoked. |
| `Pythagora-io/gpt-pilot` | Builds, but is an interactive project builder: `main.py` drives a multi-step conversation backed by a database and expects a person at each step. `--initial-prompt` seeds it; nothing makes it complete a bounded task and exit. Not invocable non-interactively. |
| `FoundationAgents/MetaGPT` | Did not build. Pins `lancedb==0.4.0`, which no longer exists on the index. A dependency conflict, and a property of the repository at this commit. |
| `smol-ai/developer` | Did not build. `setup.py` fails during metadata generation at this commit; last pushed in 2024. |
| `OpenBMB/ChatDev` | Did not build. Metadata generation fails at the root manifest. |

Three agents were blocked on one thing, a base image newer than Python 3.11, and
that is now a variable a seed line declares and a build row records. All three
build. None of the three can yet be invoked, and the reasons are worth separating.

AutoGPT and OpenHands are blocked by the same third-party wheel. `cryptography`
50.0.1 crashes the interpreter with an illegal instruction when its Rust extension
is imported on this machine, at both Python versions tested, while 45.0.7 and
42.0.8 on the same base import cleanly. Neither agent does anything wrong: each
resolves the current release of a dependency it declares, and the release is broken
on this hardware. Nothing about either agent has been measured beyond the fact that
it builds. Letting a seed declare a constraint on a transitive dependency, recorded
on the build row the way the base image and the extras already are, is the change
that would unblock both, and it is written down here rather than done quietly,
because pinning a dependency changes what is being measured and a reader has to be
able to see that it happened.

OpenManus is blocked by its own design rather than by a dependency, and no pin
would help it.

Four of the ten first agents build and install cleanly but cannot be invoked to perform a
task. Three of those four are frameworks that agents are built with rather than
agents that run, which is the distinction the submit page asks proposers to
observe and is easy to lose when counting stars.
