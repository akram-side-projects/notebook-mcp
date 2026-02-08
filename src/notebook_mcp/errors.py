class NotebookMcpError(Exception):
    pass


class NotebookNotFoundError(NotebookMcpError):
    pass


class NotebookParseError(NotebookMcpError):
    pass


class CellNotFoundError(NotebookMcpError):
    pass


class JupyterServerError(NotebookMcpError):
    pass
