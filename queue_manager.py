import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class DownloadJob:
    job_id: str
    user_id: int
    chat_id: int
    url: str
    quality: str
    label: str  # human-readable label e.g. "Link 3/10"
    callback: Callable[["DownloadJob"], Awaitable[None]] = field(repr=False)

    @staticmethod
    def make_id() -> str:
        return uuid.uuid4().hex[:12]


class DownloadQueue:
    """Async queue that processes download jobs with a fixed worker pool."""

    def __init__(self, max_workers: int = 3) -> None:
        self._queue: asyncio.Queue[DownloadJob | None] = asyncio.Queue()
        self._max_workers = max_workers
        self._workers: list[asyncio.Task] = []

    def qsize(self) -> int:
        return self._queue.qsize()

    async def start(self) -> None:
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker(i), name=f"dl-worker-{i}")
            self._workers.append(task)
        logger.info("DownloadQueue started with %d workers", self._max_workers)

    async def stop(self) -> None:
        for _ in self._workers:
            await self._queue.put(None)  # sentinel to stop each worker
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("DownloadQueue stopped")

    async def add_job(self, job: DownloadJob) -> int:
        """Add a job to the queue. Returns the queue size after adding."""
        await self._queue.put(job)
        return self._queue.qsize()

    async def _worker(self, worker_id: int) -> None:
        while True:
            job = await self._queue.get()
            if job is None:
                self._queue.task_done()
                break
            logger.info("Worker %d processing job %s (%s)", worker_id, job.job_id, job.url)
            try:
                await job.callback(job)
            except Exception as exc:
                logger.exception("Worker %d job %s failed: %s", worker_id, job.job_id, exc)
            finally:
                self._queue.task_done()
