from pathlib import Path
import pytest
from crucible.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "c.db")
    s.init_db()
    return s


def test_records_round_trip(store: Store) -> None:
    rid = store.record("candidates", slug="aider", source="github",
                       repo_url="https://github.com/Aider-AI/aider",
                       commit_sha="a" * 40)
    got = store.rows("candidates", slug="aider")
    assert len(got) == 1
    assert got[0]["id"] == rid
    assert got[0]["commit_sha"] == "a" * 40


def test_blobs_are_content_addressed_and_deduplicated(store: Store) -> None:
    a = store.blob(b"identical bytes")
    b = store.blob(b"identical bytes")
    assert a == b
    assert len(a) == 64
    assert store.read_blob(a) == b"identical bytes"


def test_records_are_append_only(store: Store) -> None:
    """A correction is a new row plus a supersedes row. Both stay readable,
    because a dataset that quietly rewrites itself cannot be audited."""
    old = store.record("builds", candidate="aider", status="failed",
                       failure_class="dependency_conflict")
    new = store.record("builds", candidate="aider", status="built",
                       image_digest="sha256:" + "b" * 64)
    store.supersede("builds", old, new, reason="retried after upstream fix")

    assert len(store.rows("builds", candidate="aider")) == 2
    sup = store.rows("supersedes")
    assert sup[0]["old_id"] == old and sup[0]["new_id"] == new


def test_there_is_no_update_method(store: Store) -> None:
    assert not hasattr(store, "update")


def test_every_row_is_timestamped(store: Store) -> None:
    rid = store.record("candidates", slug="x", source="github",
                       repo_url="u", commit_sha="c")
    assert store.rows("candidates")[0]["at"]
