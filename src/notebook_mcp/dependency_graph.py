from __future__ import annotations

from collections import defaultdict

import networkx as nx

from .models import NotebookCell


def build_dependency_edges(cells: list[NotebookCell]) -> list[tuple[str, str]]:
    last_def: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()

    for cell in cells:
        for sym in cell.uses:
            src = last_def.get(sym)
            if src and src != cell.cell_id:
                edges.add((src, cell.cell_id))

        for sym in cell.defines:
            last_def[sym] = cell.cell_id

    return sorted(edges)


def topo_sort_cells(cells: list[NotebookCell], edges: list[tuple[str, str]]) -> list[NotebookCell]:
    g = nx.DiGraph()
    for c in cells:
        g.add_node(c.cell_id)
    g.add_edges_from(edges)

    try:
        order = list(nx.topological_sort(g))
    except nx.NetworkXUnfeasible:
        # Cycles are common; fall back to file order.
        return cells

    index = {c.cell_id: i for i, c in enumerate(cells)}
    order = sorted(order, key=lambda cid: index.get(cid, 10**9))

    cell_by_id = {c.cell_id: c for c in cells}
    return [cell_by_id[cid] for cid in order if cid in cell_by_id]


def upstream_slice(
    focus_cell_id: str,
    edges: list[tuple[str, str]],
    max_cells: int,
) -> list[str]:
    preds: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        preds[b].add(a)

    selected: list[str] = []
    seen: set[str] = set()
    stack: list[str] = [focus_cell_id]

    while stack and len(selected) < max_cells:
        cid = stack.pop()
        if cid in seen:
            continue
        seen.add(cid)
        selected.append(cid)

        for p in sorted(preds.get(cid, set())):
            if p not in seen:
                stack.append(p)

    # Put focus cell last to read naturally.
    if focus_cell_id in selected:
        selected.remove(focus_cell_id)
        selected.append(focus_cell_id)

    return selected
