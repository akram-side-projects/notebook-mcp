from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class AstSummary:
    defines: set[str]
    uses: set[str]
    imports: set[str]


class _Analyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defines: set[str] = set()
        self.uses: set[str] = set()
        self.imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.defines.add(name)
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        mod = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            self.defines.add(name)
            self.imports.add(f"{mod}:{alias.name}" if mod else alias.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.defines.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.defines.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.defines.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Store):
            self.defines.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.uses.add(node.id)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:  # noqa: N802
        # Treat function args as local defines.
        self.defines.add(node.arg)
        self.generic_visit(node)


def summarize_python_source(source: str) -> AstSummary:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return AstSummary(defines=set(), uses=set(), imports=set())

    a = _Analyzer()
    a.visit(tree)

    # If a name is defined, don't treat it as a dependency use.
    uses = a.uses - a.defines

    return AstSummary(defines=a.defines, uses=uses, imports=a.imports)
