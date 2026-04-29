from unittest.mock import MagicMock

import pytest

from extractor.core.extractor import ExtractionPipeline
from extractor.exceptions import ValidationError, VLMRateLimitError


class TestExtractionPipeline:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.call.return_value = '{"name": "John", "age": "30"}'
        return client

    def test_extract_returns_valid_json(self, mock_client):
        pipeline = ExtractionPipeline(client=mock_client, max_retries=3, base_delay=0.1)
        template_str = '{"name": "", "age": ""}'
        result = pipeline.extract(template_str, ["base64_image"])

        assert result == '{"name": "John", "age": "30"}'
        mock_client.call.assert_called_once()

    def test_extract_retries_on_json_parse_error(self, mock_client):
        mock_client.call.side_effect = [
            "invalid json",
            '{"name": "John"}',
        ]
        pipeline = ExtractionPipeline(client=mock_client, max_retries=2, base_delay=0.1)
        template_str = '{"name": ""}'
        result = pipeline.extract(template_str, ["base64_image"])

        assert "John" in result
        assert mock_client.call.call_count == 2

    def test_extract_retries_on_validation_error(self, mock_client):
        mock_client.call.side_effect = [
            '{"name": "John"}',
            '{"name": "John", "age": "30"}',
        ]
        pipeline = ExtractionPipeline(client=mock_client, max_retries=2, base_delay=0.1)
        template_str = '{"name": "", "age": ""}'
        result = pipeline.extract(template_str, ["base64_image"])

        assert "age" in result
        assert mock_client.call.call_count == 2

    def test_extract_raises_after_max_retries(self, mock_client):
        mock_client.call.return_value = "invalid json"
        pipeline = ExtractionPipeline(client=mock_client, max_retries=1, base_delay=0.1)
        template_str = '{"name": ""}'

        with pytest.raises(ValidationError, match="Invalid JSON"):
            pipeline.extract(template_str, ["base64_image"])

    def test_extract_retries_on_rate_limit(self, mock_client):

        mock_client.call.side_effect = [
            VLMRateLimitError("Rate limited"),
            '{"name": "John"}',
        ]
        pipeline = ExtractionPipeline(client=mock_client, max_retries=2, base_delay=0.1)
        template_str = '{"name": ""}'
        result = pipeline.extract(template_str, ["base64_image"])

        assert "John" in result
        assert mock_client.call.call_count == 2

    def test_extract_raises_rate_limit_after_max_retries(self, mock_client):

        mock_client.call.side_effect = VLMRateLimitError("Rate limited")
        pipeline = ExtractionPipeline(client=mock_client, max_retries=1, base_delay=0.1)
        template_str = '{"name": ""}'

        with pytest.raises(VLMRateLimitError):
            pipeline.extract(template_str, ["base64_image"])
