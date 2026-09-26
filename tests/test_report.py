import json
import pytest
from pathlib import Path
from crucible.report import viability, render_markdown
from crucible.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def seed(store: Store, *, harvested: int, built: int, booted: int) -> None:
    for i in range(harvested):
        store.record("candidates", slug=f"a{i}", source="github",
                     repo_url=f"u{i}", commit_sha="a" * 40)
    for i in range(built):
        store.record("builds", candidate=f"a{i}", status="built",
                     image_digest=f"sha256:{i:064d}")
    for i in range(harvested - built):
        store.record("builds", candidate=f"z{i}", status="failed",
                     failure_class="dependency_conflict")
    for i in range(booted):
        store.record("boots", build=f"sha256:{i:064d}", status="booted")
    for i in range(built - booted):
        store.record("boots", build=f"sha256:{i:064d}", status="failed",
                     failure_class="boot_crash")


def test_counts_come_only_from_rows(store: Store) -> None:
    seed(store, harvested=10, built=6, booted=4)
    v = viability(store)
    assert (v.harvested, v.built, v.booted) == (10, 6, 4)
    assert v.by_failure["dependency_conflict"] == 4
    assert v.by_failure["boot_crash"] == 2


def test_an_empty_store_reports_zero_rather_than_guessing(store: Store) -> None:
    v = viability(store)
    assert (v.harvested, v.built, v.booted) == (0, 0, 0)
    assert v.by_failure == {}


def test_rendered_report_states_the_headline_and_contains_no_em_dash(store: Store) -> None:
    seed(store, harvested=50, built=31, booted=19)
    md = render_markdown(viability(store))
    assert "19 of 50" in md
    assert "—" not in md


def test_rendered_report_reports_percentages_it_can_derive(store: Store) -> None:
    seed(store, harvested=50, built=31, booted=19)
    md = render_markdown(viability(store))
    assert "38.0%" in md  # 19/50


def test_report_of_an_empty_store_says_so_rather_than_dividing_by_zero(store: Store) -> None:
    md = render_markdown(viability(store))
    assert "No candidates" in md


def test_rendered_report_contains_limitations_section(store: Store) -> None:
    seed(store, harvested=10, built=6, booted=4)
    md = render_markdown(viability(store))
    assert "## Limitations" in md
    assert "substring-based" in md
    assert "approximate" in md


def test_unknown_failure_class_appears_in_rendered_table(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    store.record("builds", candidate="test", status="failed",
                 failure_class="unknown")
    v = viability(store)
    assert "unknown" in v.by_failure
    md = render_markdown(v)
    assert "| unknown |" in md


def test_superseded_failed_build_then_success_counts_as_one_build(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    build1_id = store.record("builds", candidate="test", status="failed",
                             failure_class="dependency_conflict")
    build2_id = store.record("builds", candidate="test", status="built",
                             image_digest="sha256:1234")
    store.supersede("builds", build1_id, build2_id, "Retry succeeded")
    v = viability(store)
    assert v.built == 1
    assert "dependency_conflict" not in v.by_failure


def test_superseded_boot_excluded_from_count(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    store.record("builds", candidate="test", status="built",
                 image_digest="sha256:1234")
    boot1_id = store.record("boots", build="sha256:1234", status="failed",
                            failure_class="boot_crash")
    boot2_id = store.record("boots", build="sha256:1234", status="booted")
    store.supersede("boots", boot1_id, boot2_id, "Retry succeeded")
    v = viability(store)
    assert v.booted == 1
    assert "boot_crash" not in v.by_failure


def test_superseded_old_id_in_builds_does_not_suppress_boots(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    # First build gets id=1
    build1_id = store.record("builds", candidate="test", status="failed",
                             failure_class="dependency_conflict")
    # Second build gets id=2, first is superseded
    build2_id = store.record("builds", candidate="test", status="built",
                             image_digest="sha256:1234")
    store.supersede("builds", build1_id, build2_id, "Retry succeeded")
    # Boot with id=1 (same as old build id but in boots table)
    store.record("boots", build="sha256:1234", status="booted")
    v = viability(store)
    assert v.booted == 1
    assert v.built == 1


def test_normal_counts_unchanged_with_no_supersedes(store: Store) -> None:
    seed(store, harvested=10, built=6, booted=4)
    v = viability(store)
    assert (v.harvested, v.built, v.booted) == (10, 6, 4)
    assert v.by_failure["dependency_conflict"] == 4
    assert v.by_failure["boot_crash"] == 2


def test_a_second_run_of_the_same_seed_list_does_not_double_the_counts(store: Store) -> None:
    """Every published figure is a count of distinct agents, not of attempts.
    Two candidate rows for one identity, or two build rows for one candidate,
    are the same agent measured twice."""
    for _ in range(2):
        store.record("candidates", slug="a0", source="github",
                     repo_url="u0", commit_sha="a" * 40)
        store.record("builds", candidate="a0", commit_sha="a" * 40,
                     status="built", image_digest="sha256:1234")
        store.record("boots", build="sha256:1234", status="booted")

    v = viability(store)
    assert (v.harvested, v.built, v.booted) == (1, 1, 1)


def test_a_superseded_candidate_is_excluded_from_harvested(store: Store) -> None:
    """The untreated sibling of the superseded-build bug: a corrected candidate
    row sits in the denominator of the headline percentage."""
    old = store.record("candidates", slug="typo", source="github",
                       repo_url="https://github.com/x/typo", commit_sha="a" * 40)
    new = store.record("candidates", slug="fixed", source="github",
                       repo_url="https://github.com/x/fixed", commit_sha="b" * 40)
    store.supersede("candidates", old, new, "wrong repository url")

    v = viability(store)
    assert v.harvested == 1
