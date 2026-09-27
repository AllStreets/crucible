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


def test_publish_emits_failure_labels_so_the_site_never_retypes_them(tmp_path) -> None:
    """FailureClass.label is the single definition of what a class means. A
    TypeScript copy of these strings would drift silently, and the first
    symptom would be a page describing a failure as something the engine never
    meant."""
    from crucible.failures import FailureClass

    store = Store(tmp_path / "s.db")
    store.init_db()
    out = tmp_path / "public"
    publish_dataset(store, out)

    labels = json.loads((out / "labels.json").read_text())
    for cls in FailureClass:
        # Each entry carries the attribution as well as the name. The site kept
        # that set by hand in three places and two had already fallen behind the
        # classes added since; a rate driven by limits of this harness describes
        # the harness, so it is not a fact a page may quietly get wrong.
        assert labels[str(cls)]["label"] == cls.label
        assert labels[str(cls)]["attribution"] in {"harness", "repository"}


def test_the_manifest_separates_research_running_from_research_having_run(tmp_path):
    # The site claimed the research ran unattended on the strength of a pass
    # existing. Four passes existed and a person had started every one; the
    # scheduler had never executed. The two facts need separate fields or the
    # weaker one keeps standing in for the stronger.
    import json

    from crucible.publish import _research_state

    repo = tmp_path
    (repo / "runs").mkdir(parents=True)
    log = repo / "runs" / "research-passes.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in [
        {"finished": "2026-09-27T01:00:00+00:00"},                      # before the flag
        {"finished": "2026-09-27T02:00:00+00:00", "unattended": False},  # a person
        {"finished": "2026-09-27T03:00:00+00:00", "unattended": True},   # the scheduler
    ]) + "\n")
    out = repo / "site" / "public" / "data"
    out.mkdir(parents=True)

    state = _research_state(out)
    assert state["passes"] == 3
    assert state["unattended_passes"] == 1
    assert state["last_unattended_pass"] == "2026-09-27T03:00:00+00:00"
    assert state["last_pass"] == "2026-09-27T03:00:00+00:00"


def test_a_pass_that_could_not_push_says_so(tmp_path):
    import json

    from crucible.publish import _research_state

    (tmp_path / "runs").mkdir(parents=True)
    (tmp_path / "runs" / "research-passes.jsonl").write_text(
        json.dumps({"finished": "2026-09-27T03:00:00+00:00", "unattended": True,
                    "pushed": False}) + "\n")
    out = tmp_path / "site" / "public" / "data"
    out.mkdir(parents=True)
    assert _research_state(out)["last_pass_pushed"] is False
