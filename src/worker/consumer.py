import json
import sys
from pathlib import Path

import aio_pika
import aiofiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractor.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    RABBITMQ_QUEUE,
    OUTPUTS_DIR,
    TEMPLATE_PATH,
)
from extractor.core.vlm_client import OpenRouterVLMClient
from extractor.core.template_parser import load_template_schema
from extractor.utils.logger import logger


import base64


def encode_image_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"


async def on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            job_id = data["job_id"]
            file_path = data["file_path"]

            logger.info(f"Processing job: {job_id}")
            logger.info(f"Image path: {file_path}")

            template_str = load_template_schema(TEMPLATE_PATH)
            base64_image = encode_image_to_base64(file_path)

            client = OpenRouterVLMClient()
            result = client.extract_data(template_str, [base64_image])

            output_path = OUTPUTS_DIR / f"{job_id}.json"
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(result)

            logger.info(f"Job {job_id} completed. Result saved to {output_path}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise


async def main():
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
    )

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    logger.info(f"Worker listening on queue: {RABBITMQ_QUEUE}")

    await queue.consume(on_message)

    await asyncio.Future()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
