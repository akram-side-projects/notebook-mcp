import json
from pathlib import Path

import nbformat

from notebook_mcp.analyzer import analyze_notebook


def test_analyze_notebook_smoke(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell("x = 1"),
        nbformat.v4.new_code_cell("y = x + 1"),
    ]

    p = tmp_path / "t.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")

    a = analyze_notebook(str(p))
    assert len(a.cells) == 2
    assert a.dependency_edges
