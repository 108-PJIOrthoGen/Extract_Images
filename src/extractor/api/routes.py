"""API routes for image processing."""

import json
import uuid
from datetime import datetime

import aio_pika
import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from extractor.config import settings
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_images(request: Request, files: list[UploadFile] = File(...)):
    """Upload one or more images and queue them for processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    for f in files:
        if not f.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} is not an image",
            )

    job_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    job_dir = settings.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    file_paths = []
    for f in files:
        file_path = job_dir / f.filename
        async with aiofiles.open(file_path, "wb") as out:
            content = await f.read()
            await out.write(content)
        file_paths.append(str(file_path))

    message = {
        "job_id": job_id,
        "file_count": len(files),
        "file_dir": str(job_dir),
        "timestamp": timestamp,
    }

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
            "message": f"{len(files)} image(s) sent to processing queue",
        },
        status_code=202,
    )


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get extraction result by job ID."""
    output_path = settings.OUTPUTS_DIR / f"{job_id}.json"

    if not output_path.exists():
        return JSONResponse(
            content={"job_id": job_id, "status": "processing"},
            status_code=202,
        )

    async with aiofiles.open(output_path, encoding="utf-8") as f:
        result = await f.read()

    return JSONResponse(
        content={
            "job_id": job_id,
            "status": "completed",
            "data": json.loads(result),
        },
    )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
