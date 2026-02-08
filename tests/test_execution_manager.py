import asyncio

from notebook_mcp.execution_manager import ExecutionManager
from notebook_mcp.models import ExecutionTask


class _FakeWorker:
    def __init__(self, *, kernel_id: str) -> None:
        self.kernel_id = kernel_id
        self.enqueued: list[tuple[str, float]] = []
        self.is_closed = False

    def enqueue(self, task: ExecutionTask, *, timeout_s: float) -> None:
        self.enqueued.append((task.execution_id, timeout_s))

    def cancel(self, execution_id: str) -> None:
        return

    def close(self) -> None:
        self.is_closed = True


def test_multiple_executions_same_kernel_are_queued(monkeypatch) -> None:
    async def _run() -> None:
        em = ExecutionManager(base_url="http://x", token=None)

        created: list[_FakeWorker] = []

        def _fake_worker_ctor(*, base_url: str, token: str | None, kernel_id: str):  # noqa: ARG001
            w = _FakeWorker(kernel_id=kernel_id)
            created.append(w)
            return w

        monkeypatch.setattr("notebook_mcp.execution_manager.KernelWorker", _fake_worker_ctor)

        e1 = await em.submit_execution("k1", "print(1)", timeout_s=1.0)
        e2 = await em.submit_execution("k1", "print(2)", timeout_s=1.0)

        assert len(created) == 1
        assert created[0].enqueued[0][0] == e1
        assert created[0].enqueued[1][0] == e2

    asyncio.run(_run())


def test_execution_cancellation_marks_failed(monkeypatch) -> None:
    async def _run() -> None:
        em = ExecutionManager(base_url="http://x", token=None)

        def _fake_worker_ctor(*, base_url: str, token: str | None, kernel_id: str):  # noqa: ARG001
            return _FakeWorker(kernel_id=kernel_id)

        monkeypatch.setattr("notebook_mcp.execution_manager.KernelWorker", _fake_worker_ctor)

        eid = await em.submit_execution("k1", "print(1)", timeout_s=1.0)
        em.cancel_execution(eid)

        assert em.get_execution_status(eid) == "failed"
        assert "cancel" in (em._tasks[eid].error or "")

    asyncio.run(_run())


def test_kernel_restart_drops_worker(monkeypatch) -> None:
    async def _run() -> None:
        em = ExecutionManager(base_url="http://x", token=None)

        w = _FakeWorker(kernel_id="k1")

        def _fake_worker_ctor(*, base_url: str, token: str | None, kernel_id: str):  # noqa: ARG001
            return w

        monkeypatch.setattr("notebook_mcp.execution_manager.KernelWorker", _fake_worker_ctor)

        _ = await em.submit_execution("k1", "print(1)", timeout_s=1.0)
        em.drop_kernel_worker("k1")

        assert w.is_closed is True

    asyncio.run(_run())
