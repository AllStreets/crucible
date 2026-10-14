# Handoff

State of CRUCIBLE as of 2026-10-13. Everything below was read off the machine
rather than remembered. Where something is uncertain it says so.

---

## Read this first

**The research is paused and must stay paused until Connor says otherwise.**

```
com.crucible.research: PAUSED since 2026-09-29 02:49, because "working"
```

A pass holds a ~20 GB model resident for hours, and Docker's VM another 8 GB,
on the machine Connor works on. He paused it deliberately. Do not resume to
"check something". A pass is 224 runs and takes hours.

```bash
cd ~/code/CRUCIBLE
.venv/bin/crucible schedule-status     # is it paused, and does the job match its generator
.venv/bin/crucible plan                # what the parameters would run, without running it
.venv/bin/crucible resume              # ONLY when asked. Starts a pass immediately.
.venv/bin/crucible pause --reason "…" --quit-docker
```

`plan` is the safe way to answer "what would happen if". It executes nothing.

Docker is currently **quit** (the pause released it). `resume` starts it again
and waits, because a pass without the daemon records an artifact for every run
and teaches nothing.

---

## What this is

An instrument that clones real open-source agents from GitHub at pinned
commits, builds each into a container, and runs pairs of them against each
other under adversarial scenarios with deterministic criteria. It publishes the
result as papers generated from the records and a site at
<https://crucible-weld.vercel.app>.

It imports `smadp.sandbox` as a library (`~/code/SMADP`, also Connor's) and
contributes the half SMADP lacked, which is getting real agents to the starting line.
SMADP *estimates* risk with a model judge. CRUCIBLE *executes*.

Repo lives at `~/code/CRUCIBLE`, with a symlink at `~/Downloads/CRUCIBLE`. It
was moved on 2026-09-27 because macOS withholds `~/Downloads` from background
jobs, which is why the scheduler had never once run. **Do not move it back.**

---

## The record right now

| | |
|---|---|
| Pair runs | 520 (284 verdicts, 232 artifacts, 4 blocked) |
| Verdicts | 284 (155 strong, 129 weak) |
| **Confirmed attacks** | **8**, all `induced_execution` |
| Pairs with verdicts | 28 |
| Invocable agents | 8 |
| Corrections recorded | 32 supersede rows |
| Papers | 9 PDFs (2 standing, 7 per-pass) |
| Tests | 199 Python, 20 site, all green |
| Deploy | live, serving 520 pairs |

The eight invocable agents: `aider-ai-aider`, `gptme-gptme`,
`huggingface-smolagents`, `openhands-openhands`,
`openinterpreter-open-interpreter`, `qwenlm-qwen-code`,
`swe-agent-mini-swe-agent`, `ther1d-shell-gpt`.

### The finding

Every confirmed attack is `induced_execution`, and the victims are only
`swe-agent-mini-swe-agent` (7) and `openhands-openhands` (1). Six agents have
never complied across 46 verdicts. The attacker role is filled by nearly every
agent, so what separates a pair that falls from one that holds is not who
writes the instruction. It is whether the agent reading it runs what it finds.
No other scenario has confirmed in 520 runs.

All eight were checked by hand against their snapshots: staged by the plant,
marker absent at the victim's start and the attacker's exit, present at the
end, both agents exiting zero, and the victim's own output naming the command.

---

## Rules that are not negotiable

These were learned expensively. Breaking one silently corrupts the dataset.

1. **Every published figure is a count of rows.** The report takes no parameter
   that lets a figure be asserted. Papers are generated, then a verifier reads
   the finished text and refuses to emit it if any numeral is absent from the
   fact set. It has caught real errors five times.
2. **A failure is a row, never an exception.** Every stage records and
   continues.
3. **Records are append-only.** A correction is a new row plus a `supersedes`
   row. The store has no `update` method and a test asserts its absence.
4. **Entrypoints are hand-written and truthfully attributed.** `authored_by`
   records which model wrote the invocation. A wrong entrypoint is
   indistinguishable in the dataset from an agent that does not work.
5. **No model judges a result.** Criteria confirm by side effect. The one place
   a model's words appear is a question or hypothesis a person wrote, carried
   verbatim and evaluated by nothing.
6. **Never report harness failures as agent failures.** Full disk, out of
   memory, unsupported language and Python-version floors are their own classes,
   attributed to the harness wherever causes are broken down.
7. **No em dashes anywhere. No emoji.** Connor's standing preference.
8. **Push to main after each major task**, and run the tests *and read them*
   before pushing. This was violated once and caught by Connor.

---

## Architecture, briefly

```
harvest  ->  forge (docker build)  ->  env check  ->  solo gate
  ->  emit adapters  ->  arena (SMADP sandbox)  ->  classify
  ->  press (papers)  ->  publish  ->  push
```

- `crucible/store.py`, append-only SQLite, `live_rows()` is the single
  definition of "published".
- `crucible/forge.py` + `docker/generic.Dockerfile` (Python) and
  `docker/node.Dockerfile` (Node). The recipe is an experimental variable; every
  build row pins `recipe_sha`, `base_image` and any `pins`.
- `crucible/arena.py` holds `classify_run`, which decides blocked/artifact/done and
  strong/weak from the transcript and property report. Deterministic.
- `crucible/audit.py` is a *second, separately written* reading of every verdict
  against its transcript. `crucible audit` exits non-zero on any flag. It has
  caught the classifier wrong three times, including a confirmed attack that
  confirmed nothing.
- `crucible/experiment.py` holds axes and hypotheses (see below).
- `crucible/pause.py` owns the sentinel at `.crucible-paused` (repo root,
  gitignored). **Never move it under `runs/`**: a pass stages and commits that
  directory, and the first version was deleted by the pass it was meant to stop.
- `crucible/press.py` and `typeset.py` make the papers and PDFs.
- `site/` is a Next.js static export, deployed by Vercel from GitHub.

Seeds may declare `ref=v0.4.2`, `python=3.12`, `pin=cryptography==45.0.7`,
`lang=node`. Each is recorded on the build row.

---

## Research parameters

`research.yaml` is the control plane. Every pass pulls the repo and reads it, so
a committed change is the next experiment. The site's `/control` page composes
the file but deliberately cannot apply it. The gate is commit access.

An optional `experiment` block supports two things that are kept apart on
purpose:

- **An axis.** `vary: victim|attacker|scenario|model`, with `holding:` pinning
  the rest and `repeats:` running each cell more than once. Entirely mechanical.
  The model axis is coded but **has never been run**; it groups runs by model so
  each set of weights loads once.
- **A hypothesis.** `question:` and `hypothesis:` are prose, carried verbatim
  and evaluated by nothing. Only `predict: {comply: [...], hold: [...]}` is
  scored, because naming an agent and what it should do is a claim rows settle.
  The report counts how many predictions held and **never says "supported"**.

`models:` may list several models; listing them does nothing on its own, since
only an experiment that varies the model uses the list.

---

## What is covered, and what is not

CRUCIBLE publishes a map of SMADP's five risk categories (`site/public/data/coverage.json`,
rendered on `/threat-model`):

- **A** prompt injection, executed
- **B** data leakage, executed
- **C** capability conflicts, executed
- **D** cascading errors. **No executed evidence.** Needs a checkable right
  answer and a second agent acting on the first's output; every scenario here
  plants something and watches for a side effect, and a wrong answer produces no
  side effect to watch.
- **E** compliance violations. **No executed evidence.** A policy is a fact
  about an organisation, so a sandbox could only find the rule it had invented.

Every confirmed attack is A reaching C. That is a narrower claim than "8
confirmed attacks" sounds like, and the papers say so.

---

## Is this real, or one model talking to itself?

Connor asked this and it is the right question. The answer is published on
`/methodology` and computed on every publish (`provenance.json`):

- The model is **one pinned constant** on all 516 active rows, deliberately, so
  the variable is the agent.
- Eight **distinct images**, each from its own repo at its own pinned commit.
- **The divergence is the evidence.** Same scenario, same model: mini-swe-agent
  complied 7 times in 11 verdicts, OpenHands once in 4, and six agents zero
  times across 46. Identical things behave identically; these do not.

The real limitation, stated in the papers: results are about these agents driven
by *this* model. The model axis exists to test that and has not been run.

---

## Known gaps and honest uncertainties

- **The model axis has never run.** Connor's machine can take it (64 GB,
  412 GB free, `gpt-oss:20b`, `llama3.1:8b`, `qwen2.5-coder:7b` already pulled).
  He said "we can test multiple models later".
- **D and E have no evidence** and probably cannot get it without new scenarios
  with new criteria, which is SMADP work.
- **gpt-engineer** is authored but records `acted_off_task`, it writes a
  program instead of the asked-for file. Re-gated every pass.
- **Not invocable**, each with a recorded reason in
  `entrypoints/NOT-INVOCABLE.md`: AutoGPT (validates model names against a closed
  enum, so a local model cannot be named), OpenManus (installs 104 packages with
  `uv` at run time, needing egress the sandbox denies), SWE-agent, browser-use,
  swarm, langgraph, babyagi, gpt-pilot, simonw/llm, MetaGPT, ChatDev,
  smol-ai/developer, continue, opencode.
- **Papers**: Connor said "the papers might need a little more, but we'll figure
  that out later."
- **Qwen-code's engagement markers are deliberately unset.** Every held verdict
  against it grades weak until a run with it as victim shows which line means a
  tool acted. Guessing is how OpenHands' markers were wrong the first time.

---

## Things I got wrong, so you do not repeat them

- Told Connor the pause had failed when **he had resumed it himself**. Check
  before assuming a defect.
- Put the pause sentinel under `runs/`, which a pass stages and commits. The
  pass deleted its own stop signal and ran 224 runs for eight hours on a machine
  he had paused.
- Pushed with three failing tests after the test run had already told me.
- Ran `crucible resume` to "verify it works" when he had asked a question about
  it. He had to tell me to stop. **Answer questions; do not execute them.**
- Left a pass queued on his working machine without thinking about what it costs
  him while it runs.

---

## If you are picking this up

Ask what he wants before doing anything that runs. The dataset is in good shape
and can wait. Useful things that cost nothing:

- `crucible plan` to cost an experiment
- `crucible audit` over the existing record
- Site work (`cd site && npm run build`, screenshots via playwright)
- Reading `entrypoints/NOT-INVOCABLE.md`, which is where the honest accounting
  of the agent population lives

The last substantive asks, in his words, were to "keep adding entrypoints and
iterating on the site", to build the model axis (coded, not run), and that the
papers may need more.
