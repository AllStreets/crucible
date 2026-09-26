# Smoke run environment

Recorded before the run, so that a build failure can later be told apart from a
failure of the machine it ran on. A disk-exhaustion failure recorded as an agent
build failure would contaminate the distribution this project exists to publish.

- date: 2026-09-26T17:41:01Z
- docker server: 23.0.5
- host: macOS 26.4, arm64
- docker VM disk: 43G allocated of a 60G ceiling, so about 17G of headroom
- macOS free space: 413Gi
- reclaimable at start: 21.5G build cache, 18.1G images, not pruned
- seeds: seeds/smoke-five.txt (5 agents)
- store: runs/smoke.db

Nothing was pruned to make room. The images present belong to SMADP and ONEXUS
and deleting another project's artifacts to buy headroom here would be a poor
trade, so if a build fails on disk that is a reported result rather than a
silently cleared obstacle.
