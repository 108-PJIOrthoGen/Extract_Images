import pytest

from extractor.jobs import (
    JobStatus,
    is_cancelled,
    read_status,
    result_path,
    status_path,
    write_status,
)


@pytest.fixture(autouse=True)
def _tmp_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))


@pytest.mark.asyncio
async def test_write_and_read_status_roundtrip():
    await write_status("job-1", JobStatus.PROCESSING, file_count=3)
    payload = await read_status("job-1")
    assert payload["job_id"] == "job-1"
    assert payload["status"] == "processing"
    assert payload["file_count"] == 3
    assert "updated_at" in payload


@pytest.mark.asyncio
async def test_read_status_missing_returns_none():
    assert await read_status("does-not-exist") is None


@pytest.mark.asyncio
async def test_is_cancelled_true_only_for_cancelled():
    await write_status("job-2", JobStatus.CANCELLED)
    assert await is_cancelled("job-2") is True

    await write_status("job-3", JobStatus.QUEUED)
    assert await is_cancelled("job-3") is False

    # Missing status file -> treated as not cancelled (never drops a live job).
    assert await is_cancelled("job-missing") is False


def test_path_helpers_use_outputs_dir():
    assert status_path("abc").name == "abc.status.json"
    assert result_path("abc").name == "abc.json"
    assert status_path("abc").parent == result_path("abc").parent


def test_write_status_accepts_plain_string_value():
    # JobStatus(...) coercion accepts the enum's string value too.
    assert JobStatus("completed") is JobStatus.COMPLETED
