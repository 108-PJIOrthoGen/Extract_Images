"""API routes for image processing."""

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import aio_pika
import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from extractor.config import settings
from extractor.jobs import JobStatus, read_status, result_path, write_status
from extractor.loaders.constants import ALLOWED_CONTENT_TYPES, SUPPORTED_EXTENSIONS
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

MAX_FILES_PER_JOB = 25
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(name: str) -> str:
    base = Path(name).name or "image"
    cleaned = SAFE_FILENAME_RE.sub("_", base).strip("._") or "image"
    return cleaned[:128]


@router.post("/upload")
async def upload_images(request: Request, files: list[UploadFile] = File(...)):  # noqa: B008
    """Upload one or more images and queue them for processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > MAX_FILES_PER_JOB:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files (max {MAX_FILES_PER_JOB})",
        )

    job_id = str(uuid.uuid4())
    job_dir = settings.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for f in files:
        if not f.content_type or f.content_type.lower() not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} has unsupported content type {f.content_type}",
            )
        ext = Path(f.filename or "").suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} has unsupported extension",
            )

        safe_name = _sanitize_filename(f.filename or f"image{ext}")
        file_path = job_dir / safe_name

        content = await f.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} exceeds {MAX_FILE_SIZE_BYTES} bytes",
            )
        async with aiofiles.open(file_path, "wb") as out:
            await out.write(content)
        saved_paths.append(str(file_path))

    timestamp = datetime.now().isoformat()
    message = {
        "job_id": job_id,
        "file_count": len(saved_paths),
        "file_dir": str(job_dir),
        "timestamp": timestamp,
    }

    await write_status(job_id, JobStatus.QUEUED, file_count=len(saved_paths))

    channel = request.app.state.rabbitmq_channel
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=settings.RABBITMQ_QUEUE,
    )

    return JSONResponse(
        content={
            "job_id": job_id,
            "status": "queued",
            "file_count": len(saved_paths),
            "message": f"{len(saved_paths)} file(s) sent to processing queue",
        },
        status_code=202,
    )


async def _read_result(job_id: str) -> dict:
    async with aiofiles.open(result_path(job_id), encoding="utf-8") as f:
        return json.loads(await f.read())


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get extraction result by job ID."""
    output_path = result_path(job_id)
    status_payload = await read_status(job_id) or {}
    status = status_payload.get("status")

    if status == JobStatus.COMPLETED.value and output_path.exists():
        return JSONResponse(
            content={
                "job_id": job_id,
                "status": JobStatus.COMPLETED.value,
                "data": await _read_result(job_id),
                "error": None,
            },
        )

    if status == JobStatus.FAILED.value:
        return JSONResponse(
            content={
                "job_id": job_id,
                "status": JobStatus.FAILED.value,
                "data": None,
                "error": status_payload.get("error", "Extraction failed"),
            },
        )

    if status == JobStatus.CANCELLED.value:
        return JSONResponse(
            content={
                "job_id": job_id,
                "status": JobStatus.CANCELLED.value,
                "data": None,
                "error": None,
            },
        )

    if status in {JobStatus.QUEUED.value, JobStatus.PROCESSING.value}:
        return JSONResponse(
            content={
                "job_id": job_id,
                "status": status,
                "data": None,
                "error": None,
            },
            status_code=202,
        )

    if output_path.exists():
        return JSONResponse(
            content={
                "job_id": job_id,
                "status": JobStatus.COMPLETED.value,
                "data": await _read_result(job_id),
                "error": None,
            },
        )

    raise HTTPException(status_code=404, detail="Job not found")


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a job and delete its uploaded files + any result.

    Marks the job ``cancelled`` first (so the worker, which polls this status
    file at its checkpoints, drops the job instead of writing a result), then
    removes the upload directory and result JSON so nothing lingers on disk.
    Idempotent: cancelling an unknown or already-finished job is a no-op 200.
    """
    # Reject obvious path-traversal before touching the filesystem.
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise HTTPException(status_code=400, detail="Invalid job id")

    await write_status(job_id, JobStatus.CANCELLED)

    job_dir = settings.UPLOAD_DIR / job_id
    shutil.rmtree(job_dir, ignore_errors=True)
    result_path(job_id).unlink(missing_ok=True)

    logger.info("Cancelled job %s and removed its files", job_id)
    return JSONResponse(content={"job_id": job_id, "status": "cancelled"})


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
