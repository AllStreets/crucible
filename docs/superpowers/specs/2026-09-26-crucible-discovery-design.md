# CRUCIBLE discovery: finding agents without wrecking the denominator

*A recorded search stage that proposes seed lists a person confirms. 2026-09-26.*

---

## 1. What this is

The seed list holds 49 agents, hand-chosen. SMADP holds 475 scaffolded adapters.
Neither number came from a search, and both are the author's judgment about what counts as an
agent people actually run.

Discovery adds a stage before harvest that searches GitHub for repositories we have not seen,
records everything it finds, evaluates deterministic signals against each one, and writes a
dated proposal file. A person confirms the file before anything enters a run.

It does not decide what gets measured. It decides what gets *offered*.

## 2. Why the seed list stays human-confirmed

`seeds/first-fifty.txt` says, in its own header, that it holds "repositories of open-source AI
agents people actually run, not the top of a ranking." That sentence is the reason the viability
figure means anything. It is a claim about the denominator.

Automated promotion would replace that claim with a different one, silently. The measured figure
would stop being "of the agents people run, this fraction builds" and become "of the repositories
matching a keyword and sorted by stars, this fraction builds." Nothing would error. The number
would keep rendering to one decimal place and would no longer answer the question it is captioned
with.

This is the same failure shape as calling an environment check a boot, and the same shape as an
inferred entrypoint: a measurement that quietly becomes a measurement of something else. The
control is the same too. A person stays in the loop at the point where the meaning is set.

## 3. What the source probes actually returned

Measured on 2026-09-26, not assumed.

**GitHub is the source.** One narrow query, `language:python topic:ai-agents stars:>200`, returned
531 repositories. Authenticated search allows 30 queries per minute and the core API 5000 requests
per hour, which is ample for a stage that runs occasionally rather than continuously.

**HuggingFace is not, and this is worth stating because the obvious design would assume symmetry.**
A Hub search for "agent" returns model weights and datasets: quantized checkpoints, supervised
fine-tuning trajectory sets, evaluation benchmarks. A Spaces search for "autonomous agent
framework" returned an empty list. None of that is a program that can be cloned and run.

Harvesting it would not merely waste effort. Model repositories entering the candidate pool would
enter the denominator, and since none of them can build, they would drive the reported viability
rate toward zero while appearing to be a larger and more thorough study. A bigger n that measures
the wrong population is worse than a smaller one that measures the right population.

So GitHub gets a real implementation. HuggingFace Spaces gets a thin adapter behind the same
interface, written but not enabled, so that the day Spaces holds runnable agents the stage is
ready and the decision to turn it on is explicit.

## 4. Non-goals

- No automatic promotion into the candidate store. Section 2.
- No model in the classification path. Section 6.
- No HuggingFace models or datasets as agent candidates. Section 3.
- No scraping. Official APIs with an authenticated token, respecting rate limits.
- No ranking by stars as a proxy for quality. Stars are recorded, never used as a gate.

## 5. Architecture

```
  queries        declared as data, one file per query, with a written rationale
       |
  search         paginate the API; EVERY result becomes a row, accepted or not
       |
  signals        deterministic checks against repo metadata and a root listing
       |
  propose        a dated seed file plus a rejection ledger, for a person to confirm
       |
  (harvest)      only after confirmation, and only from the confirmed file
```

A query is data, not code, for the same reason an entrypoint is:

```
  queries/<slug>.json
  {
    "slug": "python-ai-agents-active",
    "source": "github",
    "query": "language:python topic:ai-agents pushed:>2026-03-01",
    "rationale": "why this query and not another; what population it is meant to
                  reach, and what it is known to miss",
    "authored_by": "human",
    "authored_at": "..."
  }
```

`rationale` is required. A query with no stated intent cannot be audited for bias, and the bias of
a search is exactly what this spec exists to keep visible.

## 6. The signals, and why none of them is a model

Each signal is a yes, no, or unknown computed from repository metadata and a listing of the root
directory. That is one to two API calls per repository, no clone, no model, no cost.

| Signal | What it checks | Why it matters |
|---|---|---|
| `llm_client` | root manifest names openai, anthropic, litellm, langchain or ollama | an agent talks to a model |
| `entrypoint` | console script, `__main__.py`, Dockerfile CMD, or a bin script | an agent can be invoked |
| `root_manifest` | pyproject, requirements or setup.py at the root | predicts our build |
| `active` | pushed within the last six months | abandoned code is a different study |
| `not_weights` | no safetensors, gguf or model-index at the root | excludes model releases |
| `not_a_list` | name and topics do not mark an awesome-list | excludes catalogues of agents |
| `license` | a license file is present, and which | we redistribute nothing, but we report it |

`not_a_list` earns its place from the probe. Searching GitHub for agents returns a large number of
curated link collections, which have every keyword an agent has and none of the code.

An ambiguous repository is recorded as ambiguous. It is not guessed at, and it is not sent to a
model. A model in this path would put a model's judgment inside the denominator of the headline
figure, which is precisely what the deterministic property floors exist to prevent in the arena.
The honest output of a stage that cannot decide is a recorded undecided, sitting in the dataset
asking to be looked at.

## 7. `root_manifest` is a falsifiable prediction, and that is the point

The first live run, five agents on 2026-09-26, failed two of them: AutoGPT and OpenHands, both for
`no_installable_manifest`. Both are monorepos whose package sits one directory below the root, and
our build recipe looks only at the root.

`root_manifest` computes that same condition from a directory listing, before any clone. So
discovery does not merely score a repository, it predicts what the build will do, and the build
either confirms the prediction or refutes it.

Recording both makes the stage falsifiable. If repositories that discovery marked `root_manifest:
no` go on to build successfully, the signal is wrong and the dataset says so without anyone having
to notice. A scoring heuristic that cannot be wrong is not a measurement, and a discovery stage
whose accuracy is never checked is how a search's bias becomes a study's conclusion.

## 8. Data model

Added to the existing append-only store. Same rules: nothing updated in place, every record pins
its inputs, a correction is a new row plus a `supersedes` row.

```
  queries       slug, source, query_string, rationale, authored_by, at
  discoveries   query, source, repo_url, repo_id, stars, pushed_at,
                license, raw_ref, at
  signals       discovery, name, value(yes|no|unknown), evidence_ref, at
  proposals     discovery, decision(propose|reject|undecided), reason,
                proposal_file, confirmed_by, confirmed_at, at
```

`discoveries` holds every result the API returned, including the ones we reject immediately. A
rejected repository is a row with a reason, never a silent omission, for the same reason a failed
build is a row. The rejection ledger is the only artifact that can answer "what did the search see
and pass over", and that question is the one a reviewer of the eventual paper will ask first.

`confirmed_by` and `confirmed_at` are null until a person confirms the proposal file. A run reads
only from confirmed proposals.

## 9. What can go wrong, and what catches it

| Risk | Control |
|---|---|
| Search bias becomes study conclusion | queries declared with rationale; every result recorded, accepted or not |
| Popularity substituted for relevance | stars recorded, never a gate; `active` uses recency, not rank |
| Model releases inflating the denominator | `not_weights`; HuggingFace models excluded by source |
| Link collections counted as agents | `not_a_list` |
| Discovery's heuristics never checked | `root_manifest` predicts the build; both stored and comparable |
| A confirmed list drifting from what was reviewed | proposals pin the file and who confirmed it |
| Rate limit exhaustion misread as no results | the API error is a row, distinct from an empty result set |

That last one matters more than it looks. A search that fails and a search that legitimately finds
nothing are indistinguishable in a naive implementation, and one of them silently shrinks the
study.

## 10. Prerequisite

The discovered population is only as meaningful as the build stage that measures it, and the build
stage currently fails every monorepo at the root. Section 7 turns that into a recorded prediction
rather than a hidden bias, but the underlying gap stays open: a recipe that looks one directory
down would change which agents are viable, and therefore what discovery is worth running against.

Fixing the recipe is not in this spec. Knowing that the numbers move when it is fixed belongs in
every report produced before then.

## 11. Open questions

1. **How many queries, and who writes them.** The bias lives in the query set. A handful written
   deliberately is defensible; a generated sweep across keyword combinations is not, and the
   difference is not visible in the output.
2. **Whether `active` at six months is right.** It excludes a genuinely finished agent that needed
   no commits. A second signal separating abandoned from complete would be more honest and is more
   work.
3. **Whether the rejection ledger is published.** It is the most useful artifact here for anyone
   auditing the selection, and it names repositories as rejected, which is a claim about other
   people's projects that deserves careful wording.
4. **Whether discovery should ever run unattended.** Confirmation is the control in section 2. A
   scheduled search that only ever appends to a rejection ledger and a proposal file breaks
   nothing, but it accumulates a queue no one reads, which is its own failure mode.
