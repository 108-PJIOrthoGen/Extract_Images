import json
from unittest.mock import MagicMock

import pytest

from extractor.core.extractor import ExtractionPipeline
from extractor.exceptions import ValidationError, VLMRateLimitError

# One image content part (shape the pipeline passes through to the client).
PARTS = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,x"}}]

# Minimal medical template the sparse payload merges into.
TEMPLATE = json.dumps(
    {
        "document": {"title": ""},
        "patient": {"full_name": ""},
        "test_results": {
            "section_1_xet_nghiem": {
                "g": {
                    "tests": [
                        {
                            "stt": 1,
                            "name": "WBC",
                            "value": None,
                            "flag": None,
                            "reference_range": "4 - 10",
                            "unit": "G/L",
                        }
                    ]
                }
            },
            "section_2_chan_doan_hinh_anh": {},
            "section_3_tham_do_chuc_nang": {},
        },
        "abnormal_flags_summary": {"HIGH": [], "LOW": [], "POSITIVE_CULTURE": []},
    }
)

# A valid SPARSE response (only the data found).
SPARSE = json.dumps(
    {"patient": {"full_name": "John"}, "groups": {"g": {"tests": [{"stt": 1, "value": 6.2}]}}}
)


class TestExtractionPipeline:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.call.return_value = SPARSE
        return client

    def test_extract_merges_sparse_into_full_template(self, mock_client):
        pipeline = ExtractionPipeline(client=mock_client, max_retries=3, base_delay=0.1)
        result = json.loads(pipeline.extract(TEMPLATE, PARTS))

        # Sparse value merged in; full structure + static fields preserved.
        assert result["patient"]["full_name"] == "John"
        wbc = result["test_results"]["section_1_xet_nghiem"]["g"]["tests"][0]
        assert wbc["value"] == 6.2
        assert wbc["name"] == "WBC" and wbc["reference_range"] == "4 - 10"
        assert "extraction_meta" in result
        mock_client.call.assert_called_once()

    def test_extract_retries_on_json_parse_error(self, mock_client):
        mock_client.call.side_effect = ["invalid json", SPARSE]
        pipeline = ExtractionPipeline(client=mock_client, max_retries=2, base_delay=0.1)
        result = json.loads(pipeline.extract(TEMPLATE, PARTS))
        assert result["patient"]["full_name"] == "John"
        assert mock_client.call.call_count == 2

    def test_extract_retries_on_bad_sparse_shape(self, mock_client):
        # A dict with no recognized sparse keys -> retry.
        mock_client.call.side_effect = [json.dumps({"foo": 1}), SPARSE]
        pipeline = ExtractionPipeline(client=mock_client, max_retries=2, base_delay=0.1)
        result = json.loads(pipeline.extract(TEMPLATE, PARTS))
        assert result["patient"]["full_name"] == "John"
        assert mock_client.call.call_count == 2

    def test_extract_raises_after_max_retries(self, mock_client):
        mock_client.call.return_value = "invalid json"
        pipeline = ExtractionPipeline(client=mock_client, max_retries=1, base_delay=0.1)
        with pytest.raises(ValidationError, match="Invalid JSON"):
            pipeline.extract(TEMPLATE, PARTS)

    def test_extract_retries_on_rate_limit(self, mock_client):
        mock_client.call.side_effect = [VLMRateLimitError("Rate limited"), SPARSE]
        pipeline = ExtractionPipeline(client=mock_client, max_retries=2, base_delay=0.1)
        result = json.loads(pipeline.extract(TEMPLATE, PARTS))
        assert result["patient"]["full_name"] == "John"
        assert mock_client.call.call_count == 2

    def test_extract_raises_rate_limit_after_max_retries(self, mock_client):
        mock_client.call.side_effect = VLMRateLimitError("Rate limited")
        pipeline = ExtractionPipeline(client=mock_client, max_retries=1, base_delay=0.1)
        with pytest.raises(VLMRateLimitError):
            pipeline.extract(TEMPLATE, PARTS)
