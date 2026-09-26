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


def seed(store: Store, *, harvested: int, built: int, checked: int) -> None:
    for i in range(harvested):
        store.record("candidates", slug=f"a{i}", source="github",
                     repo_url=f"u{i}", commit_sha="a" * 40)
    for i in range(built):
        store.record("builds", candidate=f"a{i}", commit_sha="a" * 40,
                     status="built", image_digest=f"sha256:{i:064d}")
    for i in range(harvested - built):
        store.record("builds", candidate=f"z{i}", commit_sha="a" * 40,
                     status="failed", failure_class="dependency_conflict")
    for i in range(checked):
        store.record("env_checks", build=f"sha256:{i:064d}", status="passed")
    for i in range(checked, built):
        store.record("env_checks", build=f"sha256:{i:064d}", status="failed",
                     failure_class="env_check_failed")


def test_counts_come_only_from_rows(store: Store) -> None:
    seed(store, harvested=10, built=6, checked=4)
    v = viability(store)
    assert (v.harvested, v.built, v.env_ok) == (10, 6, 4)
    assert v.by_failure["dependency_conflict"] == 4
    assert v.by_failure["env_check_failed"] == 2


def test_an_empty_store_reports_zero_rather_than_guessing(store: Store) -> None:
    v = viability(store)
    assert (v.harvested, v.built, v.env_ok) == (0, 0, 0)
    assert v.by_failure == {}


def test_rendered_report_states_the_headline_and_contains_no_em_dash(store: Store) -> None:
    seed(store, harvested=50, built=31, checked=19)
    md = render_markdown(viability(store))
    assert "19 of 50" in md
    assert "—" not in md


def test_rendered_report_reports_percentages_it_can_derive(store: Store) -> None:
    seed(store, harvested=50, built=31, checked=19)
    md = render_markdown(viability(store))
    assert "38.0%" in md  # 19/50


def test_report_of_an_empty_store_says_so_rather_than_dividing_by_zero(store: Store) -> None:
    md = render_markdown(viability(store))
    assert "No candidates" in md


def test_rendered_report_contains_limitations_section(store: Store) -> None:
    seed(store, harvested=10, built=6, checked=4)
    md = render_markdown(viability(store))
    assert "## Limitations" in md
    assert "substring-based" in md
    assert "approximate" in md


def test_unknown_failure_class_appears_in_rendered_table(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    store.record("builds", candidate="test", commit_sha="a" * 40, status="failed",
                 failure_class="unknown")
    v = viability(store)
    assert "unknown" in v.by_failure
    md = render_markdown(v)
    assert "| unknown |" in md


def test_superseded_failed_build_then_success_counts_as_one_build(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    build1_id = store.record("builds", candidate="test", commit_sha="a" * 40, status="failed",
                             failure_class="dependency_conflict")
    build2_id = store.record("builds", candidate="test", commit_sha="a" * 40, status="built",
                             image_digest="sha256:1234")
    store.supersede("builds", build1_id, build2_id, "Retry succeeded")
    v = viability(store)
    assert v.built == 1
    assert "dependency_conflict" not in v.by_failure


def test_superseded_env_check_excluded_from_count(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    store.record("builds", candidate="test", commit_sha="a" * 40, status="built",
                 image_digest="sha256:1234")
    boot1_id = store.record("env_checks", build="sha256:1234", status="failed",
                            failure_class="env_check_failed")
    boot2_id = store.record("env_checks", build="sha256:1234", status="passed")
    store.supersede("env_checks", boot1_id, boot2_id, "Retry succeeded")
    v = viability(store)
    assert v.env_ok == 1
    assert "env_check_failed" not in v.by_failure


def test_superseded_old_id_in_builds_does_not_suppress_env_checks(store: Store) -> None:
    store.record("candidates", slug="test", source="github",
                 repo_url="https://example.com", commit_sha="a" * 40)
    # First build gets id=1
    build1_id = store.record("builds", candidate="test", commit_sha="a" * 40, status="failed",
                             failure_class="dependency_conflict")
    # Second build gets id=2, first is superseded
    build2_id = store.record("builds", candidate="test", commit_sha="a" * 40, status="built",
                             image_digest="sha256:1234")
    store.supersede("builds", build1_id, build2_id, "Retry succeeded")
    # Env check with id=1 (same as the old build id, different table)
    store.record("env_checks", build="sha256:1234", status="passed")
    v = viability(store)
    assert v.env_ok == 1
    assert v.built == 1


def test_normal_counts_unchanged_with_no_supersedes(store: Store) -> None:
    seed(store, harvested=10, built=6, checked=4)
    v = viability(store)
    assert (v.harvested, v.built, v.env_ok) == (10, 6, 4)
    assert v.by_failure["dependency_conflict"] == 4
    assert v.by_failure["env_check_failed"] == 2


def test_a_second_run_of_the_same_seed_list_does_not_double_the_counts(store: Store) -> None:
    """Every published figure is a count of distinct agents, not of attempts.
    Two candidate rows for one identity, or two build rows for one candidate,
    are the same agent measured twice."""
    for _ in range(2):
        store.record("candidates", slug="a0", source="github",
                     repo_url="u0", commit_sha="a" * 40)
        store.record("builds", candidate="a0", commit_sha="a" * 40,
                     status="built", image_digest="sha256:1234")
        store.record("env_checks", build="sha256:1234", status="passed")

    v = viability(store)
    assert (v.harvested, v.built, v.env_ok) == (1, 1, 1)


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


def test_the_report_never_calls_the_environment_check_a_boot(store: Store) -> None:
    """The probe runs the image's interpreter, not the agent. A report that says
    boot, or ready, or working claims a measurement nobody made."""
    seed(store, harvested=10, built=6, checked=4)
    md = render_markdown(viability(store)).lower()
    for word in ("boot", "booted", "reached a working state"):
        assert word not in md, word


def test_the_report_says_what_was_not_measured(store: Store) -> None:
    seed(store, harvested=10, built=6, checked=4)
    md = render_markdown(viability(store))
    assert "does not measure" in md
    assert "whether the agent itself runs" in md


def test_the_failure_tables_are_labelled_per_stage_not_as_a_partition(store: Store) -> None:
    """Pooled under a heading like "where the rest failed", the table reads as a
    partition of the harvested count, which it is not and can exceed."""
    seed(store, harvested=10, built=6, checked=4)
    md = render_markdown(viability(store))
    assert "### Build stage" in md
    assert "### Container environment check stage" in md
    assert "not a partition" in md
    v = viability(store)
    assert v.build_failures == {"dependency_conflict": 4}
    assert v.env_failures == {"env_check_failed": 2}
