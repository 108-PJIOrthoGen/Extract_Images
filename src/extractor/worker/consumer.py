"""RabbitMQ worker consumer."""

import asyncio
import json
import shutil
from pathlib import Path

import aio_pika
import aiofiles

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.config import settings
from extractor.core.extractor import ExtractionPipeline
from extractor.core.template_parser import load_template_schema
from extractor.jobs import JobStatus, is_cancelled, result_path, write_status
from extractor.loaders.constants import SUPPORTED_EXTENSIONS
from extractor.loaders.image_loader import load_documents_with_manifest
from extractor.observability import setup_tracing
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)

setup_tracing("extract-worker")

_TERMINAL_STATUSES = frozenset(
    {
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    }
)


def _trusted_upload_dir(job_id: str) -> Path | None:
    """Return this job's directory only when it is directly under UPLOAD_DIR.

    RabbitMQ payloads contain a file path, but deletion must never trust that
    path: a malformed or injected message must not be able to remove arbitrary
    files.  The API creates each upload directly below the configured root.
    """
    upload_root = settings.UPLOAD_DIR.resolve()
    candidate = (upload_root / job_id).resolve()
    return candidate if candidate.parent == upload_root else None


def cleanup_upload_dir(job_id: str) -> None:
    """Remove one terminal job's source files, confined to ``UPLOAD_DIR``."""
    job_dir = _trusted_upload_dir(job_id)
    if job_dir is None:
        logger.warning("Refusing to clean upload directory for invalid job id %r", job_id)
        return

    shutil.rmtree(job_dir, ignore_errors=True)


async def cleanup_terminal_uploads() -> None:
    """Remove source files left by terminal jobs from an earlier worker run."""
    for status_file in settings.OUTPUTS_DIR.glob("*.status.json"):
        job_id = status_file.name.removesuffix(".status.json")
        try:
            async with aiofiles.open(status_file, encoding="utf-8") as f:
                status = json.loads(await f.read()).get("status")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Unable to read job status %s: %s", status_file, exc)
            continue

        if status in _TERMINAL_STATUSES:
            cleanup_upload_dir(job_id)


async def on_message(message: aio_pika.IncomingMessage):
    """Process incoming message from RabbitMQ."""
    async with message.process():
        job_id = "unknown"
        try:
            data = json.loads(message.body.decode())
            job_id = data["job_id"]
            file_dir = Path(data["file_dir"])

            # Cancelled before we picked it up — drop without touching status.
            if await is_cancelled(job_id):
                logger.info(f"Job {job_id} already cancelled — skipping")
                return

            logger.info(f"Processing job: {job_id} from {file_dir}")
            await write_status(job_id, JobStatus.PROCESSING)

            if not file_dir.exists() or not file_dir.is_dir():
                raise FileNotFoundError(f"Upload directory missing: {file_dir}")

            doc_paths = sorted(
                p
                for p in file_dir.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            if not doc_paths:
                raise ValueError("No valid images/PDFs found in upload directory")

            template_str = load_template_schema(settings.TEMPLATE_PATH)
            # Flatten all pages (PDF text/image parts + images) into one list +
            # a manifest mapping each page to its source file -> one record,
            # nothing dropped.
            content_parts, manifest = load_documents_with_manifest(doc_paths)
            if not content_parts:
                raise ValueError("No readable pages from uploaded files")
            logger.info(f"Job {job_id}: {len(content_parts)} trang tu {len(manifest)} file")

            client = OpenRouterVLMClient()
            pipeline = ExtractionPipeline(
                client=client,
                max_retries=settings.VLM_MAX_RETRIES,
                base_delay=settings.VLM_BASE_DELAY,
            )

            result = await asyncio.to_thread(
                pipeline.extract, template_str, content_parts, manifest
            )

            # The VLM call can't be interrupted; re-check once it returns so a
            # cancel that landed mid-extraction still wins — we drop the result
            # instead of resurrecting a job the user (and the API) deleted.
            if await is_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled during processing — dropping result")
                return

            output_path = result_path(job_id)
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            await write_status(job_id, JobStatus.COMPLETED, file_count=len(doc_paths))
            logger.info(f"Job {job_id} completed. Result saved to {output_path}")

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            # Don't overwrite a cancelled job with a failure (e.g. the cancel
            # deleted the upload dir mid-run, raising FileNotFoundError here).
            if await is_cancelled(job_id):
                logger.info(f"Job {job_id} was cancelled — ignoring error {e}")
                return
            try:
                await write_status(job_id, JobStatus.FAILED, error=str(e))
            except Exception as status_err:
                logger.error(f"Failed to persist failure status: {status_err}")
        finally:
            # The VLM has finished (or failed), so the original source files
            # are no longer needed.  Results and status remain in OUTPUTS_DIR
            # for the API to serve.
            if job_id != "unknown":
                cleanup_upload_dir(job_id)


async def main():
    """Main worker entry point."""
    await cleanup_terminal_uploads()

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
