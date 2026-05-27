"""RabbitMQ worker consumer."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import aio_pika
import aiofiles

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.config import settings
from extractor.core.extractor import ExtractionPipeline
from extractor.core.template_parser import load_template_schema
from extractor.loaders.image_loader import get_base64_image
from extractor.observability import setup_tracing
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)

setup_tracing("extract-worker")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def _write_status(job_id: str, status: str, **extra) -> None:
    payload = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.now().isoformat(),
        **extra,
    }
    status_path = settings.OUTPUTS_DIR / f"{job_id}.status.json"
    async with aiofiles.open(status_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(payload, ensure_ascii=False))


async def _is_cancelled(job_id: str) -> bool:
    """Check whether the API marked this job cancelled.

    The cancel endpoint writes status=cancelled and deletes the upload dir, so
    the worker polls this at its checkpoints to avoid (a) overwriting the
    cancelled status and (b) wasting a result on a job the user abandoned.
    """
    status_path = settings.OUTPUTS_DIR / f"{job_id}.status.json"
    try:
        if not status_path.exists():
            return False
        async with aiofiles.open(status_path, encoding="utf-8") as f:
            payload = json.loads(await f.read())
        return payload.get("status") == "cancelled"
    except Exception:
        return False


async def on_message(message: aio_pika.IncomingMessage):
    """Process incoming message from RabbitMQ."""
    async with message.process():
        job_id = "unknown"
        try:
            data = json.loads(message.body.decode())
            job_id = data["job_id"]
            file_dir = Path(data["file_dir"])

            # Cancelled before we picked it up — drop without touching status.
            if await _is_cancelled(job_id):
                logger.info(f"Job {job_id} already cancelled — skipping")
                return

            logger.info(f"Processing job: {job_id} from {file_dir}")
            await _write_status(job_id, "processing")

            if not file_dir.exists() or not file_dir.is_dir():
                raise FileNotFoundError(f"Upload directory missing: {file_dir}")

            image_paths = sorted(
                p for p in file_dir.iterdir()
                if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
            )
            if not image_paths:
                raise ValueError("No valid images found in upload directory")

            template_str = load_template_schema(settings.TEMPLATE_PATH)
            base64_images = [get_base64_image(str(p)) for p in image_paths]

            client = OpenRouterVLMClient()
            pipeline = ExtractionPipeline(
                client=client,
                max_retries=settings.VLM_MAX_RETRIES,
                base_delay=settings.VLM_BASE_DELAY,
            )

            result = await asyncio.to_thread(
                pipeline.extract, template_str, base64_images
            )

            # The VLM call can't be interrupted; re-check once it returns so a
            # cancel that landed mid-extraction still wins — we drop the result
            # instead of resurrecting a job the user (and the API) deleted.
            if await _is_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled during processing — dropping result")
                return

            output_path = settings.OUTPUTS_DIR / f"{job_id}.json"
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            await _write_status(job_id, "completed", file_count=len(image_paths))
            logger.info(f"Job {job_id} completed. Result saved to {output_path}")

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            # Don't overwrite a cancelled job with a failure (e.g. the cancel
            # deleted the upload dir mid-run, raising FileNotFoundError here).
            if await _is_cancelled(job_id):
                logger.info(f"Job {job_id} was cancelled — ignoring error {e}")
                return
            try:
                await _write_status(job_id, "failed", error=str(e))
            except Exception as status_err:
                logger.error(f"Failed to persist failure status: {status_err}")


async def main():
    """Main worker entry point."""
    connection = await aio_pika.connect_robust(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        login=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
    )

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)

    logger.info(f"Worker listening on queue: {settings.RABBITMQ_QUEUE}")

    await queue.consume(on_message)

    stop_event = asyncio.Event()
    await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(main())
