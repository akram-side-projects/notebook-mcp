from __future__ import annotations

from .models import NotebookCell


def format_cells_as_context(cells: list[NotebookCell]) -> str:
    parts: list[str] = []
    for c in cells:
        header = f"# --- cell: {c.cell_id} (index={c.index}, type={c.cell_type}, exec={c.execution_count}) ---"
        parts.append(header)
        if c.cell_type == "markdown":
            parts.append(c.source)
        else:
            parts.append(f"```python\n{c.source}\n```")
        parts.append("")

    return "\n".join(parts).strip() + "\n"
