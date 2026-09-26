import pytest

from crucible.press import (Facts, VerificationError, gather_facts, generate,
                            render, verify)
from crucible.store import Store


def _store(tmp_path, *, built=2, failed=1):
    store = Store(tmp_path / "s.db")
    store.init_db()
    for i in range(built):
        slug = f"ok{i}"
        digest = f"sha256:{i:064d}"
        store.record("candidates", slug=slug, source="github",
                     repo_url=f"https://github.com/x/{slug}", commit_sha="a" * 40)
        store.record("builds", candidate=slug, commit_sha="a" * 40, status="built",
                     image_digest=digest, recipe_sha="sha256:" + "r" * 64)
        store.record("env_checks", build=digest, status="passed", duration_ms=200 + i,
                     model="qwen2.5-coder:7b", base_url="http://localhost:11434/v1")
    for i in range(failed):
        slug = f"bad{i}"
        store.record("candidates", slug=slug, source="github",
                     repo_url=f"https://github.com/x/{slug}", commit_sha="b" * 40)
        store.record("builds", candidate=slug, commit_sha="b" * 40, status="failed",
                     failure_class="unsupported_language",
                     recipe_sha="sha256:" + "r" * 64)
    return store


def test_the_paper_is_generated_from_rows(tmp_path) -> None:
    doc = generate(_store(tmp_path))
    assert "3 open-source AI agent repositories" in doc
    assert "2 build successfully" in doc
    assert "66.7 percent" in doc


def test_verification_rejects_a_number_that_is_not_in_the_record(tmp_path) -> None:
    """The load-bearing test. Verification reads the finished document, not the
    inputs, because a generator that checked its own inputs would pass while
    emitting a typo, which is the failure this exists to catch.

    It is also what would make a model safe to use for connective prose later:
    the constraint that it introduce no numeral becomes a guarantee only
    because the output is read back.
    """
    facts = gather_facts(_store(tmp_path))
    doc = render(facts)

    tampered = doc.replace("We report the distribution",
                           "In 94 percent of cases we report the distribution")
    offenders = verify(tampered, facts)
    assert offenders, "a fabricated figure passed verification"
    assert any("94" in o for o in offenders)

    # The untampered document must pass, or the check is merely noisy.
    assert verify(doc, facts) == []


def test_a_stale_number_is_caught_when_the_data_moves(tmp_path) -> None:
    """The ordinary failure without any model involved: a sentence that was
    true when it was written and stopped being true when the data changed."""
    small = gather_facts(_store(tmp_path, built=2, failed=1))
    doc = render(small)
    larger = gather_facts(_store(tmp_path / "other", built=9, failed=4))
    assert verify(doc, larger), "a document from stale data passed against new facts"


def test_an_empty_record_refuses_to_produce_a_paper(tmp_path) -> None:
    """A rate over an empty denominator is undefined, not zero percent. A paper
    stating it would report a finding that was never measured."""
    store = Store(tmp_path / "empty.db")
    store.init_db()
    with pytest.raises(VerificationError, match="never measured"):
        generate(store)


def test_every_failure_cause_is_attributed_to_one_side(tmp_path) -> None:
    """The column that keeps the headline rate honest. A rate driven by harness
    limits says something about the harness, and a reader cannot tell the two
    apart from a class name alone."""
    doc = generate(_store(tmp_path))
    assert "Attributable to" in doc
    assert "this harness" in doc


def test_limitations_are_generated_rather_than_composed(tmp_path) -> None:
    """Composed limitations fall out of date with the results above them."""
    doc = generate(_store(tmp_path, built=5, failed=2))
    assert "Sample size is 7 repositories" in doc
    assert "No agent was invoked" in doc
