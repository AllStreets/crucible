# Container viability of open-source AI agents

*Generated from run records. Every figure below is a count of rows.*

## Abstract

We attempt to build 10 open-source AI agent repositories into containers at pinned commits and to start each resulting image in a network-denied sandbox. 6 build successfully and 6 pass a container environment check, a rate of 60.0 percent. We report the distribution of failure causes and, for each, whether the cause is a property of the agent or a limit of the harness. We do not measure whether any agent runs.

## Method

Each repository is resolved to a commit SHA, cloned inside a container build at that pin, and installed using a single generic recipe. The resulting image is started with egress denied and runs an environment probe: the interpreter starts, prints one line, and exits.

The probe does not invoke the agent. The container command overrides whatever entrypoint the agent defines, so a passing check establishes that the environment works and nothing more. The repositories studied share no common entrypoint, and with no network and no credentials an invocation would measure the harness rather than the agent.

Records span 2026-09-26 to 2026-09-26. Build recipes used: 1. A recipe digest is pinned on every build row, since the recipe determines which agents are buildable and rows produced under different recipes are different measurements.

## Results

| Stage | Count |
|---|---|
| Repositories harvested | 10 |
| Seed URLs unresolved | 0 |
| Built | 6 |
| Build failed | 4 |
| Environment check passed | 6 |
| Environment check failed | 0 |

Failure counts are tallies of recorded rows and are not a partition of the repositories harvested. A repository that fails to build contributes a build row and no check row, so the tables below neither sum to the harvested count nor are bounded by it.

### Build stage

| Cause | Count | Attributable to |
|---|---|---|
| Written in a language this recipe does not build | 2 | this harness |
| The manifest found is a workspace root, not an installable package | 2 | this harness |

### Environment check stage

No environment check failures recorded.

Probe durations range from 208 to 267 milliseconds.

## Threats to validity

**The headline rate is not a property of the agents alone.** The attribution column above separates causes that are facts about a repository from causes that are limits of this harness. A reader comparing this rate against another study must check that the harness limits are comparable, because extending the recipe changes the rate without any agent changing.

**Failure classification is substring based.** Unmatched failures are recorded as unclassified rather than assigned to a nearest class. The unclassified bucket also holds failures of the harness itself, including a build exceeding its timeout and the container runtime failing to start, because filing either under a build cause would attribute it to the agent.

**Selection.** The repositories studied were chosen by hand as agents people run together, not sampled from a ranking. The rate therefore describes that population and does not generalise to all repositories matching an agent keyword.

## Limitations

Generated from run metadata rather than composed, so these cannot fall out of date with the results above.

- Sample size is 10 repositories.
- Models held constant across checks: 1.
- Build recipes in the record: 1. A rate computed across more than one recipe is not a single measurement.
- No agent was invoked, so nothing here is evidence of agent behaviour.
- No pair of agents was run, so nothing here concerns interaction.

## Reproduction

Every figure resolves to a row in the published dataset, and every recorded failure to its full build log, addressed by content hash.
