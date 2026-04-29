"""RabbitMQ worker consumer."""

import asyncio
import json

import aio_pika
import aiofiles

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.config import settings
from extractor.core.extractor import ExtractionPipeline
from extractor.core.template_parser import load_template_schema
from extractor.loaders.image_loader import get_base64_image
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


async def on_message(message: aio_pika.IncomingMessage):
    """Process incoming message from RabbitMQ."""
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            job_id = data["job_id"]
            file_path = data["file_path"]

            logger.info(f"Processing job: {job_id}")
            logger.info(f"Image path: {file_path}")

            template_str = load_template_schema(settings.TEMPLATE_PATH)
            base64_image = get_base64_image(file_path)

            client = OpenRouterVLMClient()
            pipeline = ExtractionPipeline(
                client=client,
                max_retries=settings.VLM_MAX_RETRIES,
                base_delay=settings.VLM_BASE_DELAY,
            )

            # Run sync extraction in thread pool
            result = await asyncio.to_thread(pipeline.extract, template_str, [base64_image])

            output_path = settings.OUTPUTS_DIR / f"{job_id}.json"
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            logger.info(f"Job {job_id} completed. Result saved to {output_path}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise


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
