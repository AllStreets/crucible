"""What the executed evidence is evidence for."""
from __future__ import annotations


def test_a_category_with_no_executed_scenario_says_so():
    # The useful half of this map. A dataset with five hundred runs still says
    # nothing about a category no scenario reaches, and a page that reported
    # only the run count would let a reader assume otherwise.
    from crucible.coverage import coverage

    got = {c["key"]: c for c in coverage({"induced_execution", "secret_exfiltration",
                                          "partner_escalation", "state_poisoning"})}
    assert got["A"]["covered"] and got["B"]["covered"] and got["C"]["covered"]
    assert not got["D"]["covered"], "no adversarial scenario has the shape D needs"
    assert not got["E"]["covered"], "a policy is a fact about an organisation"
    for key in ("D", "E"):
        assert got[key]["why_absent"], "an uncovered category must say why"


def test_coverage_follows_what_actually_ran():
    from crucible.coverage import coverage

    none_run = {c["key"]: c["covered"] for c in coverage(set())}
    assert not any(none_run.values()), "nothing is covered before anything runs"

    only_canary = {c["key"]: c["covered"] for c in coverage({"secret_exfiltration"})}
    assert only_canary["B"] and not only_canary["A"] and not only_canary["C"]
