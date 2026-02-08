from __future__ import annotations

from pathlib import Path

import nbformat

from .errors import NotebookNotFoundError, NotebookParseError


def load_notebook(path: str) -> nbformat.NotebookNode:
    p = Path(path)
    if not p.exists():
        raise NotebookNotFoundError(f"Notebook not found: {path}")

    try:
        return nbformat.read(str(p), as_version=4)
    except Exception as e:  # noqa: BLE001
        raise NotebookParseError(f"Failed to parse notebook: {path}") from e


def strip_outputs_inplace(nb: nbformat.NotebookNode) -> None:
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            # Preserve execution_count. It is useful for offline execution-state heuristics.
