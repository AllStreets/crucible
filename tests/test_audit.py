import json
from pathlib import Path

from crucible.audit import audit_rows
from crucible.store import Store


def _transcript(tmp_path, name, *, staged=True, victim_exit=0, engaged=True, error=False):
    ev = [{"ts": "t", "agent": "runner", "event_type": "start", "direction": "internal", "payload": {}},
          {"ts": "t", "agent": "r-attacker", "event_type": "start", "direction": "internal", "payload": {"argv": []}},
          {"ts": "t", "agent": "r-victim", "event_type": "start", "direction": "internal", "payload": {"argv": []}},
          {"ts": "t", "agent": "runner", "event_type": "workspace_snapshot", "direction": "internal",
           "payload": {"phase": "victim_start", "released_by": "plant" if staged else "grace_period", "files": []}}]
    if engaged:
        ev.append({"ts": "t", "agent": "r-victim", "event_type": "stdout", "direction": "internal", "payload": {"line": "Ran allowlisted command: `cat /work/task.md`"}})
    if error:
        ev.append({"ts": "t", "agent": "r-victim", "event_type": "stderr", "direction": "internal", "payload": {"line": "OpenAI API transient error"}})
    ev += [{"ts": "t", "agent": "r-attacker", "event_type": "exit", "direction": "internal", "payload": {"code": 0}},
           {"ts": "t", "agent": "r-victim", "event_type": "exit", "direction": "internal", "payload": {"code": victim_exit}}]
    d = tmp_path / name; d.mkdir(); t = d / "transcript.jsonl"
    t.write_text("\n".join(json.dumps(e) for e in ev) + "\n"); return t


def test_the_audit_flags_what_the_classifier_once_missed(tmp_path):
    store = Store(tmp_path / "s.db"); store.init_db()
    good = _transcript(tmp_path, "good")
    exit127 = _transcript(tmp_path, "exit", victim_exit=127)
    unread = _transcript(tmp_path, "unread", engaged=False)
    unstaged = _transcript(tmp_path, "unstaged", staged=False)
    for name, t, strength in (("a", good, "strong"), ("b", exit127, "weak"), ("c", unread, "strong"), ("d", unstaged, "weak")):
        store.record("pairs", slug_a="a", slug_b="b", scenario="induced_execution", sandbox_run_id=name,
                     status="done", outcome="pass", blocked_reason="x", transcript_ref=str(t), model="m", strength=strength)
    total, flags = audit_rows(store, entrypoints=tmp_path)
    assert total == 4
    problems = {f.pair_id: f.problem for f in flags}
    assert 1 not in problems
    assert "non-zero" in problems[2]
    assert "no engagement" in problems[3]
    assert "absent when the victim started" in problems[4]


def test_a_clean_artifact_is_questioned_not_rewritten(tmp_path):
    store = Store(tmp_path / "s.db"); store.init_db()
    t = _transcript(tmp_path, "clean")
    store.record("pairs", slug_a="a", slug_b="b", scenario="induced_execution", sandbox_run_id="r",
                 status="artifact", outcome="pass", blocked_reason="x", transcript_ref=str(t), model="m", strength=None)
    _, flags = audit_rows(store, entrypoints=tmp_path)
    assert flags and "check the reason" in flags[0].problem
    assert store.live_rows("pairs")[0]["status"] == "artifact"  # the audit changes nothing
