from notebook_mcp.dependency_graph import build_dependency_edges
from notebook_mcp.models import NotebookCell


def test_build_dependency_edges() -> None:
    cells = [
        NotebookCell(
            cell_id="a",
            index=0,
            cell_type="code",
            source="x = 1",
            execution_count=None,
            source_hash="h1",
            defines=["x"],
            uses=[],
            imports=[],
        ),
        NotebookCell(
            cell_id="b",
            index=1,
            cell_type="code",
            source="y = x + 1",
            execution_count=None,
            source_hash="h2",
            defines=["y"],
            uses=["x"],
            imports=[],
        ),
    ]

    edges = build_dependency_edges(cells)
    assert edges == [("a", "b")]
