from __future__ import annotations

from collections import defaultdict, deque

from .models import NotebookAnalysis, NotebookCell, NotebookCellState, NotebookRerunPlan, NotebookState


def _build_preds_succs(edges: list[tuple[str, str]]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    preds: dict[str, set[str]] = defaultdict(set)
    succs: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        preds[b].add(a)
        succs[a].add(b)
    return preds, succs


def _upstream_closure(focus_cell_id: str, preds: dict[str, set[str]]) -> list[str]:
    seen: set[str] = set()
    q: deque[str] = deque([focus_cell_id])
    ordered: list[str] = []

    while q:
        cid = q.popleft()
        if cid in seen:
            continue
        seen.add(cid)
        ordered.append(cid)
        for p in sorted(preds.get(cid, set())):
            if p not in seen:
                q.append(p)

    # focus last
    if focus_cell_id in ordered:
        ordered.remove(focus_cell_id)
        ordered.append(focus_cell_id)

    return ordered


def compute_notebook_state(analysis: NotebookAnalysis) -> NotebookState:
    cell_by_id: dict[str, NotebookCell] = {c.cell_id: c for c in analysis.cells}
    preds, _ = _build_preds_succs(analysis.dependency_edges)

    states: list[NotebookCellState] = []

    for c in analysis.cells:
        exec_count = c.execution_count
        if exec_count is None:
            status = "unexecuted"
            states.append(
                NotebookCellState(
                    cell_id=c.cell_id,
                    status=status,
                    execution_count=exec_count,
                    stale_reasons=[],
                    upstream_cell_ids=sorted(preds.get(c.cell_id, set())),
                )
            )
            continue

        stale_reasons: list[str] = []
        for p in sorted(preds.get(c.cell_id, set())):
            pc = cell_by_id.get(p)
            if not pc:
                continue
            if pc.execution_count is None:
                stale_reasons.append(f"depends_on_unexecuted:{p}")
            elif pc.execution_count > exec_count:
                stale_reasons.append(f"depends_on_newer_execution:{p}")

        status = "stale" if stale_reasons else "executed"

        states.append(
            NotebookCellState(
                cell_id=c.cell_id,
                status=status,
                execution_count=exec_count,
                stale_reasons=stale_reasons,
                upstream_cell_ids=sorted(preds.get(c.cell_id, set())),
            )
        )

    return NotebookState(path=analysis.path, cells=states)


def build_rerun_plan(analysis: NotebookAnalysis, focus_cell_id: str) -> NotebookRerunPlan:
    state = compute_notebook_state(analysis)
    state_by_id = {s.cell_id: s for s in state.cells}

    preds, _ = _build_preds_succs(analysis.dependency_edges)
    upstream_ids = _upstream_closure(focus_cell_id, preds)

    cells_to_rerun: list[str] = []
    reasons: dict[str, list[str]] = {}

    for cid in upstream_ids:
        s = state_by_id.get(cid)
        if not s:
            continue

        if s.status == "unexecuted":
            cells_to_rerun.append(cid)
            reasons[cid] = ["unexecuted"]
        elif s.status == "stale":
            cells_to_rerun.append(cid)
            reasons[cid] = list(s.stale_reasons)

    # Ensure focus cell is included as final action.
    if focus_cell_id not in cells_to_rerun:
        cells_to_rerun.append(focus_cell_id)
        reasons.setdefault(focus_cell_id, []).append("focus")

    # Remove duplicates, preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for cid in cells_to_rerun:
        if cid in seen:
            continue
        seen.add(cid)
        deduped.append(cid)

    return NotebookRerunPlan(
        path=analysis.path,
        focus_cell_id=focus_cell_id,
        cells_to_rerun=deduped,
        reasons_by_cell_id=reasons,
    )
