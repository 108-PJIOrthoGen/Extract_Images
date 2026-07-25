"""FastAPI application factory."""

from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI

from extractor.api.routes import router
from extractor.config import settings
from extractor.observability import setup_tracing
from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)

_tracing_enabled = setup_tracing("extract-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage RabbitMQ connection lifecycle."""
    app.state.rabbitmq_connection = await aio_pika.connect_robust(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        login=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
    )
    app.state.rabbitmq_channel = await app.state.rabbitmq_connection.channel()
    await app.state.rabbitmq_channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)
    logger.info("RabbitMQ connection established")
    yield
    if app.state.rabbitmq_connection and not app.state.rabbitmq_connection.is_closed:
        await app.state.rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Image Processing API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    if _tracing_enabled:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
