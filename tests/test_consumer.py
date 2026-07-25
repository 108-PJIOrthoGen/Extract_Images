import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from extractor.jobs import JobStatus
from extractor.worker.consumer import on_message


def _message(body: dict | bytes) -> MagicMock:
    msg = MagicMock()
    msg.body = body if isinstance(body, bytes) else json.dumps(body).encode()
    # MagicMock() supports the async context manager protocol (3.8+), so
    # ``async with message.process():`` works out of the box.
    msg.process = MagicMock()
    return msg


class TestConsumer:
    @pytest.mark.asyncio
    async def test_on_message_processes_job(self, tmp_path):
        upload = tmp_path / "job"
        upload.mkdir()
        (upload / "image.png").write_bytes(b"fake")
        msg = _message({"job_id": "job-123", "file_dir": str(upload)})

        parts = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,x"}}]
        manifest = [
            {
                "file": "image.png",
                "type": "image",
                "mode": "image",
                "pages": 1,
                "page_start": 1,
                "page_end": 1,
            }
        ]

        with (
            patch("extractor.worker.consumer.write_status", new=AsyncMock()) as write,
            patch("extractor.worker.consumer.is_cancelled", new=AsyncMock(return_value=False)),
            patch("extractor.worker.consumer.result_path", return_value=tmp_path / "out.json"),
            patch("extractor.worker.consumer.load_template_schema", return_value='{"name": ""}'),
            patch(
                "extractor.worker.consumer.load_documents_with_manifest",
                return_value=(parts, manifest),
            ),
            patch("extractor.worker.consumer.ExtractionPipeline") as pipeline,
        ):
            pipeline.return_value.extract = MagicMock(return_value='{"name": "John"}')
            await on_message(msg)

        msg.process.assert_called_once()
        # Job moved processing -> completed.
        statuses = [c.args[1] for c in write.await_args_list]
        assert JobStatus.PROCESSING in statuses
        assert JobStatus.COMPLETED in statuses
        assert (tmp_path / "out.json").read_text() == '{"name": "John"}'

    @pytest.mark.asyncio
    async def test_on_message_writes_failed_on_invalid_json(self):
        msg = _message(b"invalid json")
        with (
            patch("extractor.worker.consumer.write_status", new=AsyncMock()) as write,
            patch("extractor.worker.consumer.is_cancelled", new=AsyncMock(return_value=False)),
        ):
            # Errors are handled, not re-raised.
            await on_message(msg)
        assert write.await_args.args[1] == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_on_message_writes_failed_on_missing_fields(self):
        msg = _message({"job_id": "test"})  # no file_dir
        with (
            patch("extractor.worker.consumer.write_status", new=AsyncMock()) as write,
            patch("extractor.worker.consumer.is_cancelled", new=AsyncMock(return_value=False)),
        ):
            await on_message(msg)
        assert write.await_args.args[0] == "test"
        assert write.await_args.args[1] == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_on_message_writes_failed_on_template_error(self, tmp_path):
        upload = tmp_path / "job"
        upload.mkdir()
        (upload / "image.png").write_bytes(b"fake")
        msg = _message({"job_id": "job-x", "file_dir": str(upload)})

        with (
            patch("extractor.worker.consumer.write_status", new=AsyncMock()) as write,
            patch("extractor.worker.consumer.is_cancelled", new=AsyncMock(return_value=False)),
            patch(
                "extractor.worker.consumer.load_template_schema",
                side_effect=Exception("Template error"),
            ),
        ):
            await on_message(msg)
        assert write.await_args.args[1] == JobStatus.FAILED
        assert "Template error" in write.await_args.kwargs.get("error", "")

    @pytest.mark.asyncio
    async def test_on_message_skips_cancelled_job(self, tmp_path):
        msg = _message({"job_id": "cancelled-1", "file_dir": str(tmp_path)})
        with (
            patch("extractor.worker.consumer.write_status", new=AsyncMock()) as write,
            patch("extractor.worker.consumer.is_cancelled", new=AsyncMock(return_value=True)),
        ):
            await on_message(msg)
        # Cancelled before pickup -> no status writes at all.
        write.assert_not_awaited()
