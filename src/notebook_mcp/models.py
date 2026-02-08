from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class NotebookCell(BaseModel):
    cell_id: str
    index: int
    cell_type: Literal["code", "markdown", "raw"]
    source: str
    execution_count: int | None = None
    source_hash: str

    defines: list[str] = Field(default_factory=list)
    uses: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)


class NotebookAnalysis(BaseModel):
    path: str
    nbformat: int
    nbformat_minor: int
    cells: list[NotebookCell]

    dependency_edges: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Directed edges (from_cell_id, to_cell_id)",
    )


class FocusedContext(BaseModel):
    path: str
    focus_cell_id: str | None = None
    selected_cell_ids: list[str]
    context_text: str


CellStatus = Literal["unexecuted", "executed", "stale", "unknown"]


class NotebookCellState(BaseModel):
    cell_id: str
    status: CellStatus
    execution_count: int | None = None
    stale_reasons: list[str] = Field(default_factory=list)
    upstream_cell_ids: list[str] = Field(default_factory=list)


class NotebookState(BaseModel):
    path: str
    cells: list[NotebookCellState]


class NotebookRerunPlan(BaseModel):
    path: str
    focus_cell_id: str
    cells_to_rerun: list[str]
    reasons_by_cell_id: dict[str, list[str]] = Field(default_factory=dict)


class JupyterSession(BaseModel):
    id: str
    path: str | None = None
    name: str | None = None
    type: str | None = None
    kernel_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class JupyterKernel(BaseModel):
    id: str
    name: str | None = None
    last_activity: str | None = None
    execution_state: str | None = None
    connections: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


ExecutionStatus = Literal["pending", "running", "completed", "failed"]


class ExecutionTask(BaseModel):
    execution_id: str
    kernel_id: str
    code: str
    status: ExecutionStatus
    outputs: list = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    error: str | None = None
