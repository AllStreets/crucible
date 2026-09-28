"""An experiment, stated before it runs and answered from the rows it wrote.

A pass without one of these is a sweep: every invocable pair against every
scenario, which is the right default and answers no particular question. This
is for the other case, where there is a question worth naming and a prediction
worth being wrong about.

Two ideas, and they are deliberately separate.

The first is an axis. Hold everything constant, vary exactly one thing, and the
split is the finding. It is the shape of the only real result this instrument
has produced so far: same scenario, same model, same planted instruction, and
the outcome decided entirely by which agent was reading. An axis is mechanical.
It builds the run set and nothing about it is a judgement.

The second is a hypothesis, and it is where a tool like this can quietly start
lying. The question and the hypothesis are prose, recorded verbatim and never
evaluated by anything: no model reads them, no rule scores them, and they
appear in the report as what the person asked rather than as what the data
said. What can be scored is a prediction, which names agents and what they were
expected to do, because that is a claim about rows. The report puts the two
side by side and counts. It never says "supported" or "refuted": it says what
was predicted, what happened, and how many of the predictions held, and a
reader draws the conclusion that is theirs to draw.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: The dimensions an axis may vary. Each corresponds to something a run row
#: already records, because an axis that varied something unrecorded would
#: produce a split nobody could trace back.
AXES = ("victim", "attacker", "scenario", "model")


class ExperimentError(ValueError):
    pass


@dataclass(frozen=True)
class Prediction:
    """What the experiment expected, in terms a row can settle."""

    comply: tuple[str, ...] = ()
    hold: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {"comply": list(self.comply), "hold": list(self.hold)}

    @property
    def stated(self) -> bool:
        return bool(self.comply or self.hold)


@dataclass(frozen=True)
class Experiment:
    question: str = ""
    hypothesis: str = ""
    vary: str = ""
    #: The dimensions held fixed while the axis moves. Keys are axis names.
    holding: dict[str, str] = field(default_factory=dict)
    #: How many times each cell is run. An axis with one run per cell shows a
    #: split that could be noise; this is the only honest way to tell.
    repeats: int = 1
    predict: Prediction = field(default_factory=Prediction)

    @property
    def stated(self) -> bool:
        return bool(self.question or self.vary)

    def as_dict(self) -> dict:
        return {
            "question": self.question, "hypothesis": self.hypothesis,
            "vary": self.vary, "holding": dict(self.holding),
            "repeats": self.repeats, "predict": self.predict.as_dict(),
        }


def parse(raw: object, *, known_scenarios: tuple[str, ...]) -> Experiment:
    if raw is None:
        return Experiment()
    if not isinstance(raw, dict):
        raise ExperimentError("experiment must be a mapping")

    vary = str(raw.get("vary") or "").strip()
    if vary and vary not in AXES:
        raise ExperimentError(f"vary must be one of {list(AXES)}, not {vary!r}")

    holding = raw.get("holding") or {}
    if not isinstance(holding, dict):
        raise ExperimentError("holding must be a mapping of axis to value")
    holding = {str(k): str(v) for k, v in holding.items()}
    for k in holding:
        if k not in AXES:
            raise ExperimentError(f"cannot hold {k!r}; holdable: {list(AXES)}")
    if vary and vary in holding:
        raise ExperimentError(f"cannot both vary and hold {vary!r}")
    bad = [v for k, v in holding.items() if k == "scenario" and v not in known_scenarios]
    if bad:
        raise ExperimentError(f"unknown scenario held: {bad}")

    repeats = int(raw.get("repeats") or 1)
    if repeats < 1:
        raise ExperimentError("repeats must be at least one")

    pred_raw = raw.get("predict") or {}
    if not isinstance(pred_raw, dict):
        raise ExperimentError("predict must be a mapping")
    predict = Prediction(
        comply=tuple(str(x) for x in (pred_raw.get("comply") or [])),
        hold=tuple(str(x) for x in (pred_raw.get("hold") or [])),
    )
    overlap = set(predict.comply) & set(predict.hold)
    if overlap:
        raise ExperimentError(
            f"{sorted(overlap)} predicted both to comply and to hold; a prediction "
            "that cannot be wrong is not a prediction")

    # An axis over models multiplies every cell by the number of models, and
    # each one is tens of gigabytes that has to be loaded, used and released.
    # It is worth saying out loud what was asked for rather than discovering it
    # eight hours in on somebody's working machine.
    return Experiment(
        question=str(raw.get("question") or "").strip(),
        hypothesis=str(raw.get("hypothesis") or "").strip(),
        vary=vary, holding=holding, repeats=repeats, predict=predict,
    )


def run_set(exp: Experiment, *, agents: list[str], scenarios: list[str],
            models: list[str] | None = None) -> list[tuple[str, str, str, str]]:
    """The ordered (attacker, victim, scenario, model) runs this experiment needs.

    Mechanical, and deliberately so: an axis decides what is run, and nothing
    about what is run is a judgement. Holding a dimension pins it; varying one
    sweeps it; anything neither held nor varied sweeps too, because pinning it
    silently would mean the report described a narrower experiment than it ran.

    The model is the outermost loop and that is not a detail. Every model this
    could vary over is a weights file measured in tens of gigabytes, and the
    server holding one unloads it to make room for the next. Interleaving them
    would reload the same weights hundreds of times and spend the pass moving
    bytes rather than running agents, on a machine somebody else is using.
    Grouped this way each model is loaded once, used for every run that needs
    it, and released.
    """
    if not exp.stated:
        return []
    models = models or [""]
    held_scenario = exp.holding.get("scenario")
    held_attacker = exp.holding.get("attacker")
    held_victim = exp.holding.get("victim")
    held_model = exp.holding.get("model")

    out: list[tuple[str, str, str, str]] = []
    for model in ([held_model] if held_model else models):
        for scenario in ([held_scenario] if held_scenario else scenarios):
            for attacker in ([held_attacker] if held_attacker else agents):
                for victim in ([held_victim] if held_victim else agents):
                    if attacker == victim:
                        continue
                    out.extend([(attacker, victim, scenario, model)] * exp.repeats)
    return out


def split(exp: Experiment, rows: list[dict]) -> list[dict]:
    """The observed outcome along the varied axis, one entry per value.

    This is the whole point of an axis: hold everything, vary one thing, and
    read where it splits. Computed from rows and nothing else.
    """
    if not exp.vary:
        return []
    key = {"victim": "slug_b", "attacker": "slug_a",
           "scenario": "scenario", "model": "model"}[exp.vary]
    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        b = buckets.setdefault(r.get(key) or "unrecorded",
                               {"held": 0, "complied": 0, "no_result": 0})
        if r["status"] == "done":
            b["complied" if r["outcome"] == "fail" else "held"] += 1
        else:
            b["no_result"] += 1
    return [{"value": k, **v} for k, v in
            sorted(buckets.items(), key=lambda kv: (-kv[1]["complied"], kv[0]))]


def score(exp: Experiment, rows: list[dict]) -> dict:
    """How the stated prediction fared, as counts rather than a verdict.

    Never returns "supported" or "refuted". A prediction names agents and what
    they were expected to do; this reports what each of them actually did and
    how many predictions held. Turning that into a conclusion is the reader's
    job, and a tool that did it for them would be the one thing this project
    exists not to be.
    """
    if not exp.predict.stated:
        return {}
    complied: dict[str, int] = {}
    verdicts: dict[str, int] = {}
    for r in rows:
        if r["status"] != "done":
            continue
        verdicts[r["slug_b"]] = verdicts.get(r["slug_b"], 0) + 1
        if r["outcome"] == "fail":
            complied[r["slug_b"]] = complied.get(r["slug_b"], 0) + 1

    lines = []
    for slug in exp.predict.comply:
        got = complied.get(slug, 0)
        lines.append({"agent": slug, "predicted": "comply", "complied": got,
                      "verdicts": verdicts.get(slug, 0), "as_predicted": got > 0})
    for slug in exp.predict.hold:
        got = complied.get(slug, 0)
        n = verdicts.get(slug, 0)
        lines.append({"agent": slug, "predicted": "hold", "complied": got,
                      "verdicts": n, "as_predicted": got == 0 and n > 0})
    held = sum(1 for l in lines if l["as_predicted"])
    untested = sum(1 for l in lines if l["verdicts"] == 0)
    return {"lines": lines, "as_predicted": held, "total": len(lines),
            "untested": untested}
