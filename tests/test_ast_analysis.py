from notebook_mcp.ast_analysis import summarize_python_source


def test_summarize_python_source_defines_uses_imports() -> None:
    src = """
import os
from math import sqrt as sq

x = 1

def foo(a):
    return x + a + sq(4)
"""
    s = summarize_python_source(src)

    assert "os" in s.defines
    assert "x" in s.defines
    assert "foo" in s.defines

    assert "sq" in s.defines
    assert "math:sqrt" in s.imports

    assert "x" not in s.uses
    assert "a" not in s.uses
