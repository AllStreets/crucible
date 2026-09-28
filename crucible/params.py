"""Research parameters, read from research.yaml at the repository root.

A pass is defined by a file rather than by flags so that the definition of the
experiment is versioned with its results. Every published dataset carries the
parameters it was produced under, and a change to them is a commit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ADVERSARIAL = ("secret_exfiltration", "induced_execution", "state_poisoning", "partner_escalation")


@dataclass(frozen=True)
class Params:
    model: str = "qwen3-coder:30b-a3b-q4_K_M"
    ollama: str = "http://localhost:11434/v1"
    scenarios: tuple[str, ...] = ADVERSARIAL
    agents: tuple[str, ...] | str = "all-invocable"
    rounds: int = 1
    seeds: tuple[str, ...] = ()
    cadence_hours: int = 6
    pull: bool = True
    source: str = "defaults"
    #: An optional question this pass exists to answer. Absent for an ordinary
    #: sweep, which is the right default and answers nothing in particular.
    experiment: "Experiment" = field(default_factory=lambda: __import__(
        "crucible.experiment", fromlist=["Experiment"]).Experiment())

    def as_dict(self) -> dict:
        return {
            "model": self.model, "ollama": self.ollama, "scenarios": list(self.scenarios),
            "agents": self.agents if isinstance(self.agents, str) else list(self.agents),
            "rounds": self.rounds, "seeds": list(self.seeds), "cadence_hours": self.cadence_hours,
            "pull": self.pull, "source": self.source,
            **({"experiment": self.experiment.as_dict()}
               if self.experiment.stated else {}),
        }


class ParamsError(ValueError):
    pass


def load_params(repo: Path) -> Params:
    path = repo / "research.yaml"
    if not path.exists():
        return Params()
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ParamsError("research.yaml must be a mapping")

    from crucible.experiment import parse as parse_experiment

    scenarios = tuple(raw.get("scenarios") or ADVERSARIAL)
    unknown = [s for s in scenarios if s not in ADVERSARIAL]
    if unknown:
        raise ParamsError(f"unknown scenarios {unknown}; known: {list(ADVERSARIAL)}")

    agents = raw.get("agents", "all-invocable")
    if isinstance(agents, list):
        agents = tuple(str(a) for a in agents)
    elif agents != "all-invocable":
        raise ParamsError("agents must be 'all-invocable' or a list of slugs")

    rounds = int(raw.get("rounds", 1))
    if rounds < 1:
        raise ParamsError("rounds must be at least 1")
    cadence = int(raw.get("cadence_hours", 6))
    if cadence < 1:
        raise ParamsError("cadence_hours must be at least 1")

    return Params(
        model=str(raw.get("model", Params.model)),
        ollama=str(raw.get("ollama", Params.ollama)),
        scenarios=scenarios, agents=agents, rounds=rounds,
        seeds=tuple(str(s) for s in (raw.get("seeds") or [])),
        cadence_hours=cadence, pull=bool(raw.get("pull", True)),
        source=str(path.relative_to(repo)),
        experiment=parse_experiment(raw.get("experiment"),
                                    known_scenarios=ADVERSARIAL),
    )
