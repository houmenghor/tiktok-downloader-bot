"""
DownloadJob and DownloadQueue
─────────────────────────────
Data structure used: asyncio.Queue (FIFO)
  - O(1) enqueue and dequeue
  - Thread-safe for concurrent asyncio tasks
  - Fixed worker pool (max_workers) consumes jobs concurrently

Also keeps a bounded deque of recently completed jobs for /history or debug.
"""
import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# Max recent completed jobs to keep in memory
_HISTORY_LIMIT = 200


@dataclass
class DownloadJob:
    user_id: int
    chat_id: int
    url: str
    quality: str
    label: str                           # e.g. "Link 3/10"
    callback: Callable[["DownloadJob"], Awaitable[None]] = field(repr=False)
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    # If True: save file to save_dir locally; do NOT upload to Telegram chat
    save_locally: bool = False
    save_dir: str | None = None          # target folder when save_locally=True


class DownloadQueue:
    """Async FIFO queue with a fixed-size worker pool.

    Multiple users submit jobs concurrently.
    Workers pick jobs in arrival order (fair scheduling).
    """

    def __init__(self, max_workers: int = 3) -> None:
        self._queue: asyncio.Queue[DownloadJob | None] = asyncio.Queue()
        self._max_workers = max_workers
        self._workers: list[asyncio.Task] = []
        # Bounded ring buffer for completed job IDs (for diagnostics)
        self._history: deque[str] = deque(maxlen=_HISTORY_LIMIT)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker(i), name=f"dl-worker-{i}")
            self._workers.append(task)
        logger.info("DownloadQueue started — %d workers", self._max_workers)

    async def stop(self) -> None:
        for _ in self._workers:
            await self._queue.put(None)          # sentinel per worker
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("DownloadQueue stopped")

    # ── Public API ───────────────────────────────────────────────────────────

    async def add_job(self, job: DownloadJob) -> int:
        """Enqueue a job. Returns current queue depth AFTER insertion."""
        await self._queue.put(job)
        return self._queue.qsize()

    def qsize(self) -> int:
        return self._queue.qsize()

    @property
    def recent_jobs(self) -> list[str]:
        return list(self._history)

    # ── Worker ───────────────────────────────────────────────────────────────

    async def _worker(self, worker_id: int) -> None:
        while True:
            job = await self._queue.get()
            if job is None:                      # shutdown sentinel
                self._queue.task_done()
                break
            logger.info("Worker[%d] → job %s | %s | %s", worker_id, job.job_id, job.quality, job.url)
            try:
                await job.callback(job)
                self._history.append(job.job_id)
            except Exception as exc:
                logger.exception("Worker[%d] job %s raised: %s", worker_id, job.job_id, exc)
            finally:
                self._queue.task_done()
