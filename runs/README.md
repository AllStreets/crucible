# Runs

The first CRUCIBLE results produced against a live Docker daemon, committed
whole rather than summarised. Every count in `smoke-report.md` resolves to a row
in `smoke.db`, and every failure row resolves to its full build log in `blobs/`,
addressed by sha256. A reader who doubts a number can check it here.

- `smoke-environment.md`  machine and disk state, recorded before the run
- `smoke-five.txt`        the seed list, in `../seeds/`
- `smoke.db`              the append-only record store
- `blobs/`                build logs, content addressed
- `smoke-report.md`       the report, generated from the store
- `smoke-run.log`         stdout of the run itself
