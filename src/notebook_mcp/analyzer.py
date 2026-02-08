from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from .ast_analysis import summarize_python_source
from .context_builder import format_cells_as_context
from .dependency_graph import build_dependency_edges, topo_sort_cells, upstream_slice
from .errors import CellNotFoundError
from .models import FocusedContext, NotebookAnalysis, NotebookCell
from .notebook_io import load_notebook, strip_outputs_inplace
from .utils import normalize_newlines, sha256_text


def _cell_id(cell: dict, index: int) -> str:
    # Jupyter notebooks may include a stable 'id' field (nbformat 4.5+).
    cid = cell.get("id")
    if isinstance(cid, str) and cid.strip():
        return cid
    return f"cell_{index}"  # stable fallback


def analyze_notebook(
    path: str,
    *,
    include_markdown: bool = True,
    strip_outputs: bool = True,
    cell_types: tuple[str, ...] = ("code", "markdown"),
) -> NotebookAnalysis:
    mtime = os.path.getmtime(path)
    return _analyze_notebook_cached(
        path,
        mtime,
        include_markdown=include_markdown,
        strip_outputs=strip_outputs,
        cell_types=cell_types,
    )


@lru_cache(maxsize=32)
def _analyze_notebook_cached(
    path: str,
    mtime: float,
    *,
    include_markdown: bool,
    strip_outputs: bool,
    cell_types: tuple[str, ...],
) -> NotebookAnalysis:
    nb = load_notebook(path)
    if strip_outputs:
        strip_outputs_inplace(nb)

    out_cells: list[NotebookCell] = []

    for i, cell in enumerate(nb.get("cells", [])):
        ctype = cell.get("cell_type")
        if ctype not in cell_types:
            continue
        if ctype == "markdown" and not include_markdown:
            continue

        source = normalize_newlines(cell.get("source") or "")
        h = sha256_text(source)

        defines: list[str] = []
        uses: list[str] = []
        imports: list[str] = []

        if ctype == "code":
            s = summarize_python_source(source)
            defines = sorted(s.defines)
            uses = sorted(s.uses)
            imports = sorted(s.imports)

        out_cells.append(
            NotebookCell(
                cell_id=_cell_id(cell, i),
                index=i,
                cell_type=ctype,
                source=source,
                execution_count=cell.get("execution_count"),
                source_hash=h,
                defines=defines,
                uses=uses,
                imports=imports,
            )
        )

    edges = build_dependency_edges(out_cells)

    return NotebookAnalysis(
        path=str(Path(path)),
        nbformat=int(nb.get("nbformat", 4)),
        nbformat_minor=int(nb.get("nbformat_minor", 0)),
        cells=out_cells,
        dependency_edges=edges,
    )


def get_focused_context(
    path: str,
    *,
    focus_cell_id: str,
    max_cells: int = 25,
    include_markdown: bool = True,
) -> FocusedContext:
    analysis = analyze_notebook(path, include_markdown=include_markdown)
    if focus_cell_id not in {c.cell_id for c in analysis.cells}:
        raise CellNotFoundError(f"Cell not found: {focus_cell_id}")

    selected_ids = upstream_slice(focus_cell_id, analysis.dependency_edges, max_cells=max_cells)

    cell_by_id = {c.cell_id: c for c in analysis.cells}
    selected_cells = [cell_by_id[cid] for cid in selected_ids if cid in cell_by_id]

    # Make output readable: topo order within selected cells when possible.
    selected_edges = [(a, b) for (a, b) in analysis.dependency_edges if a in selected_ids and b in selected_ids]
    selected_cells = topo_sort_cells(selected_cells, selected_edges)

    context_text = format_cells_as_context(selected_cells)

    return FocusedContext(
        path=analysis.path,
        focus_cell_id=focus_cell_id,
        selected_cell_ids=[c.cell_id for c in selected_cells],
        context_text=context_text,
    )


def export_notebook_to_script(
    path: str,
    *,
    include_markdown_as_comments: bool = False,
) -> str:
    analysis = analyze_notebook(path, include_markdown=True, strip_outputs=True)

    code_cells: list[NotebookCell] = []
    for c in analysis.cells:
        if c.cell_type == "code":
            code_cells.append(c)
        elif c.cell_type == "markdown" and include_markdown_as_comments:
            # Keep markdown as a docstring-ish block to preserve narrative.
            code_cells.append(
                c.model_copy(update={"cell_type": "code", "source": f"\n\"\"\"\n{c.source}\n\"\"\"\n"})
            )

    ordered = topo_sort_cells(code_cells, analysis.dependency_edges)

    parts: list[str] = []
    parts.append(f"# Generated from notebook: {analysis.path}\n")

    for c in ordered:
        parts.append(f"# --- cell: {c.cell_id} (index={c.index}) ---")
        parts.append(c.source.rstrip())
        parts.append("")

    return "\n".join(parts).strip() + "\n"
