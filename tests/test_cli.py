"""The CLI's contract is main(argv) -> int. A traceback out of it is a defect.

Nothing here touches Docker, git or the network: the only subcommand exercised
against a real store is `report`, and the `run` paths tested are the ones that
return before any runner is called.
"""
from pathlib import Path

from crucible.cli import main


def test_a_missing_seed_file_is_a_legible_message_and_a_nonzero_code(tmp_path, capsys) -> None:
    code = main(["run", str(tmp_path / "nope.txt"), "--db", str(tmp_path / "c.db")])
    out = capsys.readouterr().out
    assert code != 0
    assert "no seed file" in out
    assert "nope.txt" in out
    assert "Traceback" not in out


def test_a_missing_seed_file_creates_no_database(tmp_path) -> None:
    db = tmp_path / "data" / "c.db"
    main(["run", str(tmp_path / "nope.txt"), "--db", str(db)])
    assert not db.exists()


def test_report_on_an_empty_store_says_so_and_returns_zero(tmp_path, capsys) -> None:
    code = main(["report", "--db", str(tmp_path / "c.db")])
    out = capsys.readouterr().out
    assert code == 0
    assert "No candidates have been harvested yet" in out


def test_a_seed_file_of_only_comments_runs_and_reports_nothing(tmp_path, capsys) -> None:
    seeds = tmp_path / "seeds.txt"
    seeds.write_text("# a comment\n\n   # an indented comment\n")
    code = main(["run", str(seeds), "--db", str(tmp_path / "c.db")])
    out = capsys.readouterr().out
    assert code == 0
    assert "No candidates have been harvested yet" in out


def test_no_cli_output_contains_an_em_dash(tmp_path, capsys) -> None:
    main(["report", "--db", str(tmp_path / "c.db")])
    assert "—" not in capsys.readouterr().out
