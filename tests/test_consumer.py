import json
from unittest.mock import MagicMock, patch

import pytest

from extractor.worker.consumer import on_message


class TestConsumer:
    @pytest.mark.asyncio
    async def test_on_message_processes_job(self):
        mock_message = MagicMock()
        mock_message.body = json.dumps(
            {"job_id": "test-job-123", "file_path": "/fake/path/image.png"}
        ).encode()

        mock_message.process = MagicMock()

        with patch("extractor.worker.consumer.load_template_schema") as mock_load_template:
            mock_load_template.return_value = '{"name": ""}'

            with patch("extractor.worker.consumer.get_base64_image") as mock_get_b64:
                mock_get_b64.return_value = "data:image/png;base64,fake"

                with patch("extractor.worker.consumer.ExtractionPipeline") as mock_pipeline:
                    mock_pipeline_instance = MagicMock()
                    mock_pipeline_instance.extract = MagicMock(return_value='{"name": "John"}')
                    mock_pipeline.return_value = mock_pipeline_instance

                    with patch("extractor.worker.consumer.settings") as mock_settings:
                        mock_settings.OUTPUTS_DIR = MagicMock()
                        mock_settings.OUTPUTS_DIR.__truediv__ = MagicMock(return_value=MagicMock())

                        await on_message(mock_message)

                        mock_message.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_raises_on_invalid_json():
        mock_message = MagicMock()
        mock_message.body = b"invalid json"

        with pytest.raises(json.JSONDecodeError):
            await on_message(mock_message)

    @pytest.mark.asyncio
    async def test_on_message_raises_on_missing_fields():
        mock_message = MagicMock()
        mock_message.body = json.dumps({"job_id": "test"}).encode()

        with pytest.raises(KeyError):
            await on_message(mock_message)

    @pytest.mark.asyncio
    async def test_on_message_logs_error_and_raises():
        mock_message = MagicMock()
        mock_message.body = json.dumps(
            {"job_id": "test-job", "file_path": "/fake/path.png"}
        ).encode()

        with patch(
            "extractor.worker.consumer.load_template_schema",
            side_effect=Exception("Template error"),
        ), pytest.raises(Exception, match="Template error"):
            await on_message(mock_message)
