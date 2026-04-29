from unittest.mock import MagicMock, patch

import pytest
import requests

from extractor.clients.vlm_client import OpenRouterVLMClient
from extractor.exceptions import VLMAuthError, VLMRateLimitError


class TestOpenRouterVLMClient:
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_client_initializes_with_defaults(self):
        client = OpenRouterVLMClient()
        assert client.api_key == "test-key"
        assert client.model == "google/gemini-1.5-pro"

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_client_accepts_custom_api_key_and_model(self):
        client = OpenRouterVLMClient(api_key="custom-key", model="custom-model")
        assert client.api_key == "custom-key"
        assert client.model == "custom-model"

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""})
    def test_client_raises_auth_error_on_empty_key(self):
        with pytest.raises(VLMAuthError):
            OpenRouterVLMClient()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "your_openrouter_api_key_here"})
    def test_client_raises_auth_error_on_placeholder_key(self):
        with pytest.raises(VLMAuthError):
            OpenRouterVLMClient()

    @patch("extractor.clients.vlm_client.requests.post")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_call_returns_clean_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '```json\n{"key": "value"}\n```'}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = OpenRouterVLMClient()
        result = client.call("prompt", ["base64_image"])

        assert result == '{"key": "value"}'
        mock_post.assert_called_once()

    @patch("extractor.clients.vlm_client.requests.post")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_call_raises_auth_error_on_401(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = error

        mock_post.return_value = mock_response

        client = OpenRouterVLMClient()
        with pytest.raises(VLMAuthError):
            client.call("prompt", ["base64_image"])

    @patch("extractor.clients.vlm_client.requests.post")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_call_raises_rate_limit_error_on_429(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = error

        mock_post.return_value = mock_response

        client = OpenRouterVLMClient()
        with pytest.raises(VLMRateLimitError):
            client.call("prompt", ["base64_image"])
