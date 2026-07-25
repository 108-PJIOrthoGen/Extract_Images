"""On-disk store for job status and results.

A job leaves two files in ``OUTPUTS_DIR``:

- ``{job_id}.status.json`` -- the lifecycle state polled by ``GET /result`` and
  by the worker's cancel checkpoints.
- ``{job_id}.json`` -- the final extraction result, written once on completion.

Both the API and the worker share these helpers so the read/write logic and the
status vocabulary live in exactly one place.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

import aiofiles

from extractor.config import settings
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


class JobStatus(str, Enum):
    """Lifecycle states a job moves through."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def status_path(job_id: str) -> Path:
    """Path to a job's status file."""
    return settings.OUTPUTS_DIR / f"{job_id}.status.json"


def result_path(job_id: str) -> Path:
    """Path to a job's result file."""
    return settings.OUTPUTS_DIR / f"{job_id}.json"


async def write_status(job_id: str, status: JobStatus, **extra) -> None:
    """Persist a job's status (with an ``updated_at`` timestamp)."""
    payload = {
        "job_id": job_id,
        "status": JobStatus(status).value,
        "updated_at": datetime.now().isoformat(),
        **extra,
    }
    async with aiofiles.open(status_path(job_id), "w", encoding="utf-8") as f:
        await f.write(json.dumps(payload, ensure_ascii=False))


async def read_status(job_id: str) -> dict | None:
    """Return a job's status payload, or ``None`` if it has no status file."""
    path = status_path(job_id)
    if not path.exists():
        return None
    async with aiofiles.open(path, encoding="utf-8") as f:
        return json.loads(await f.read())


async def is_cancelled(job_id: str) -> bool:
    """Return True if the job has been marked cancelled.

    The cancel endpoint writes ``status=cancelled`` and deletes the upload dir,
    so the worker polls this at its checkpoints to avoid overwriting the
    cancelled status or wasting a result on an abandoned job. Errors are treated
    as "not cancelled" so a transient read failure never drops a live job.
    """
    try:
        payload = await read_status(job_id)
    except Exception:
        return False
    if not payload:
        return False
    return payload.get("status") == JobStatus.CANCELLED.value
