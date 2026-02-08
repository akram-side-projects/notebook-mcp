import json
from pathlib import Path

import nbformat

from notebook_mcp.analyzer import analyze_notebook
from notebook_mcp.state_engine import build_rerun_plan, compute_notebook_state


def test_state_engine_marks_stale_when_dependency_executed_later(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()

    c1 = nbformat.v4.new_code_cell("x = 1")
    c1.execution_count = 2

    c2 = nbformat.v4.new_code_cell("y = x + 1")
    c2.execution_count = 1

    nb.cells = [c1, c2]

    p = tmp_path / "t.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")

    analysis = analyze_notebook(str(p))
    state = compute_notebook_state(analysis)
    by_id = {s.cell_id: s for s in state.cells}

    # second cell depends on x, but x was executed after it (exec_count 2 > 1)
    assert by_id[analysis.cells[1].cell_id].status == "stale"


def test_rerun_plan_includes_upstream_and_focus(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()

    c1 = nbformat.v4.new_code_cell("x = 1")
    c1.execution_count = None

    c2 = nbformat.v4.new_code_cell("y = x + 1")
    c2.execution_count = 1

    nb.cells = [c1, c2]

    p = tmp_path / "t.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")

    analysis = analyze_notebook(str(p))
    focus = analysis.cells[1].cell_id

    plan = build_rerun_plan(analysis, focus_cell_id=focus)
    assert focus in plan.cells_to_rerun
    assert analysis.cells[0].cell_id in plan.cells_to_rerun
