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


def test_record_rejects_unknown_column(store: Store) -> None:
    """Column names are validated to prevent mutation paths."""
    with pytest.raises(ValueError) as exc:
        store.record("candidates", slug="x", source="github", repo_url="u",
                     commit_sha="c", unknown_col="bad")
    assert "unknown_col" in str(exc.value)


def test_rows_rejects_unknown_where_key(store: Store) -> None:
    """Where clause identifiers are validated."""
    store.record("candidates", slug="x", source="github",
                 repo_url="u", commit_sha="c")
    with pytest.raises(ValueError) as exc:
        store.rows("candidates", unknown_key="value")
    assert "unknown_key" in str(exc.value)


def test_list_round_trips(store: Store) -> None:
    """Lists in JSON columns round-trip as lists."""
    digests = ["sha256:" + "a" * 64, "sha256:" + "b" * 64]
    rid = store.record("runs", scenario="test", scenario_version="1",
                       roles=["agent", "observer"], image_digests=digests,
                       model="gpt4", model_version="latest", seed=42,
                       status="running")
    rows = store.rows("runs")
    assert len(rows) == 1
    assert isinstance(rows[0]["roles"], list)
    assert isinstance(rows[0]["image_digests"], list)
    assert rows[0]["image_digests"] == digests


def test_dict_round_trips(store: Store) -> None:
    """Dicts in JSON columns round-trip as dicts."""
    roles_dict = ["agent", "observer"]
    rid = store.record("runs", scenario="test", scenario_version="1",
                       roles=roles_dict, image_digests=["digest1", "digest2"],
                       model="gpt4", model_version="latest", seed=42,
                       status="running")
    rows = store.rows("runs")
    assert isinstance(rows[0]["roles"], list)
    assert rows[0]["roles"] == roles_dict


def test_plain_string_round_trips(store: Store) -> None:
    """Plain strings in JSON columns round-trip unchanged."""
    store.record("runs", scenario="plain_string", scenario_version="1",
                 roles="simple_string", image_digests="another_string",
                 model="gpt4", model_version="latest", seed=42,
                 status="running")
    rows = store.rows("runs")
    assert rows[0]["roles"] == "simple_string"
    assert rows[0]["image_digests"] == "another_string"


def test_string_starting_with_bracket_round_trips(store: Store) -> None:
    """Strings starting with brackets round-trip unchanged."""
    bracket_string = "[not valid json"
    store.record("runs", scenario="bracket", scenario_version="1",
                 roles=bracket_string, image_digests=bracket_string,
                 model="gpt4", model_version="latest", seed=42,
                 status="running")
    rows = store.rows("runs")
    assert rows[0]["roles"] == bracket_string
    assert rows[0]["image_digests"] == bracket_string


def test_a_rejected_record_writes_nothing(store: Store) -> None:
    """Columns are validated before the row is stamped and before anything is
    written: a timestamp is a fact about a row being written, and a rejected
    call writes no row."""
    with pytest.raises(ValueError):
        store.record("candidates", slug="x", source="github", repo_url="u",
                     commit_sha="c", nonsense="bad")
    assert store.rows("candidates") == []


def test_declared_credentials_round_trip_as_a_list(store: Store) -> None:
    store.record("candidates", slug="x", source="github", repo_url="u",
                 commit_sha="c", credentials=["GITHUB_TOKEN"])
    assert store.rows("candidates")[0]["credentials"] == ["GITHUB_TOKEN"]


def test_a_store_written_before_a_column_existed_gains_it(tmp_path):
    # CREATE TABLE IF NOT EXISTS says nothing about a table whose shape has
    # changed, so without a migration the first write naming a new column
    # raises against every store that already holds rows. The rows that
    # predate the column keep NULL, which is the truthful value.
    import sqlite3

    from crucible.store import Store

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE builds (id INTEGER PRIMARY KEY, candidate TEXT NOT NULL,"
        " commit_sha TEXT, status TEXT NOT NULL, failure_class TEXT,"
        " image_digest TEXT, log_ref TEXT, recipe_sha TEXT, extras TEXT,"
        " at TEXT NOT NULL);"
        "INSERT INTO builds (candidate, status, at) VALUES ('old', 'built', 't');")
    conn.commit(); conn.close()

    store = Store(db)
    store.init_db()
    store.record("builds", candidate="new", status="built", base_image="python:3.12-slim")
    rows = {r["candidate"]: r["base_image"] for r in store.live_rows("builds")}
    assert rows["old"] is None
    assert rows["new"] == "python:3.12-slim"
