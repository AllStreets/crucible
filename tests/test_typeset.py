from pathlib import Path

from crucible.typeset import render_pdf


def test_a_paper_typesets_to_more_than_one_page(tmp_path: Path) -> None:
    doc = "# A title\n\n*standfirst*\n\n## Abstract\n\n" + ("Words. " * 200 + "\n\n") * 6 + \
          "## Results\n\n| A | B |\n|---|---|\n| x | 1 |\n\n- a bullet\n"
    pages = render_pdf(doc, tmp_path / "p.pdf", engine_commit="abc123", dataset_sha256="d" * 64,
                       figures={"Results": [("x", 1, "earned"), ("y", 3, "artifact")]})
    assert pages >= 2
    data = (tmp_path / "p.pdf").read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 4000
