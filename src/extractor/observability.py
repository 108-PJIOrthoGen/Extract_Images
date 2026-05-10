"""OpenTelemetry tracing bootstrap.

Activated only when OTEL_EXPORTER_OTLP_ENDPOINT is set (no-op otherwise).
Auto-instruments outgoing HTTP requests and aio-pika RabbitMQ traffic; the
caller is responsible for instrumenting a FastAPI app via
``FastAPIInstrumentor.instrument_app(app)`` after ``setup_tracing`` returns.
"""

import os

from extractor.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_tracing(default_service_name: str) -> bool:
    """Configure tracing if OTEL_EXPORTER_OTLP_ENDPOINT is set.

    Returns True when tracing was configured, False when skipped.
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        logger.warning("OpenTelemetry packages missing; tracing disabled: %s", exc)
        return False

    service_name = os.getenv("OTEL_SERVICE_NAME", default_service_name)
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    AioPikaInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    logger.info("OTel tracing enabled — service=%s endpoint=%s", service_name, endpoint)
    return True
