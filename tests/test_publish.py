import json

from crucible.publish import publish_dataset
from crucible.store import Store


def test_publish_writes_a_dataset_a_schema_and_a_manifest(tmp_path) -> None:
    store = Store(tmp_path / "s.db")
    store.init_db()
    store.record("candidates", slug="a", source="github",
                 repo_url="https://github.com/x/a", commit_sha="c" * 40)
    store.record("builds", candidate="a", commit_sha="c" * 40, status="built",
                 image_digest="sha256:" + "d" * 64, recipe_sha="sha256:" + "e" * 64)
    out = tmp_path / "public"
    result = publish_dataset(store, out)

    assert (out / "dataset.json").exists()
    assert (out / "schema.json").exists()
    assert (out / "manifest.json").exists()

    data = json.loads((out / "dataset.json").read_text())
    assert data["builds"][0]["candidate"] == "a"
    assert data["builds"][0]["recipe_sha"] == "sha256:" + "e" * 64
    assert result.counts["builds"] == 1


def test_publish_excludes_superseded_rows(tmp_path) -> None:
    """A correction is a new row plus a supersedes row. Publishing both would
    double count, and the site would report more builds than happened."""
    store = Store(tmp_path / "s.db")
    store.init_db()
    first = store.record("builds", candidate="a", status="failed")
    second = store.record("builds", candidate="a", status="built")
    store.supersede("builds", first, second, "rebuilt after the recipe was fixed")

    result = publish_dataset(store, tmp_path / "public")
    assert result.counts["builds"] == 1

    data = json.loads((tmp_path / "public" / "dataset.json").read_text())
    assert [r["status"] for r in data["builds"]] == ["built"]


def test_the_manifest_pins_the_dataset_it_describes(tmp_path) -> None:
    """The sha256 must be of the bytes actually written. A manifest whose digest
    does not match its dataset is worse than no manifest, because it invites a
    reader to trust a file that was changed after it was described."""
    import hashlib
    store = Store(tmp_path / "s.db")
    store.init_db()
    store.record("builds", candidate="a", status="built")
    out = tmp_path / "public"
    publish_dataset(store, out)

    body = (out / "dataset.json").read_text()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["dataset_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert manifest["counts"]["builds"] == 1
