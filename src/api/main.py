import json
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
import aio_pika
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from extractor.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_QUEUE,
    UPLOAD_DIR,
    OUTPUTS_DIR,
)

app = FastAPI(title="Image Processing API", version="1.0.0")

connection = None
channel = None


async def get_channel():
    global connection, channel
    if connection is None or connection.is_closed:
        connection = await aio_pika.connect_robust(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            login=RABBITMQ_USER,
            password=RABBITMQ_PASSWORD,
        )
        channel = await connection.channel()
        await channel.declare_queue(RABBITMQ_QUEUE, durable=True)
    return channel


@app.on_event("shutdown")
async def shutdown_event():
    global connection
    if connection and not connection.is_closed:
        await connection.close()


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    job_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    file_ext = Path(file.filename).suffix
    file_name = f"{job_id}{file_ext}"
    file_path = UPLOAD_DIR / file_name

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    message = {
        "job_id": job_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "timestamp": timestamp,
    }

    channel = await get_channel()
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=RABBITMQ_QUEUE,
    )

    return JSONResponse(
        content={"job_id": job_id, "status": "queued", "message": "Image sent to processing queue"},
        status_code=202,
    )


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    output_path = OUTPUTS_DIR / f"{job_id}.json"

    if not output_path.exists():
        return JSONResponse(
            content={"job_id": job_id, "status": "processing"},
            status_code=202,
        )

    async with aiofiles.open(output_path, "r", encoding="utf-8") as f:
        result = await f.read()

    return JSONResponse(
        content={"job_id": job_id, "status": "completed", "data": json.loads(result)},
    )


@app.get("/health")
async def health():
    return {"status": "healthy"}
