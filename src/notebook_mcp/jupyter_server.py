from __future__ import annotations

from typing import Any

import httpx

from .errors import JupyterServerError
from .models import JupyterKernel, JupyterSession


class JupyterServerClient:
    def __init__(self, base_url: str, token: str | None = None, timeout_s: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(timeout=timeout_s)

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"token {self.token}"}

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            r = self._client.get(url, headers=self._headers())
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            raise JupyterServerError(f"Jupyter request failed: GET {url}") from e

    def list_sessions(self) -> list[JupyterSession]:
        data = self._get("/api/sessions")
        out: list[JupyterSession] = []
        for s in data:
            kernel = s.get("kernel") or {}
            out.append(
                JupyterSession(
                    id=str(s.get("id") or ""),
                    path=s.get("path"),
                    name=s.get("name"),
                    type=s.get("type"),
                    kernel_id=kernel.get("id"),
                    raw=s,
                )
            )
        return out

    def get_kernel(self, kernel_id: str) -> JupyterKernel:
        k = self._get(f"/api/kernels/{kernel_id}")
        return JupyterKernel(
            id=str(k.get("id") or kernel_id),
            name=k.get("name"),
            last_activity=k.get("last_activity"),
            execution_state=k.get("execution_state"),
            connections=k.get("connections"),
            raw=k,
        )

    def close(self) -> None:
        self._client.close()
