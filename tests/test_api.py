import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from extractor.api.app import create_app
from extractor.jobs import JobStatus, result_path, write_status


@pytest.fixture
def app(tmp_path, monkeypatch):
    # The settings dir properties honour these env overrides, so the API reads
    # and writes job files under the test's tmp dir.
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    application = create_app()
    # httpx's ASGITransport does not run lifespan, so wire the queue channel
    # ourselves instead of connecting to RabbitMQ.
    channel = MagicMock()
    channel.default_exchange.publish = AsyncMock()
    application.state.rabbitmq_channel = channel
    return application


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health_endpoint(app):
    async with _client(app) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_upload_returns_202(app):
    async with _client(app) as client:
        response = await client.post(
            "/upload",
            files={"files": ("test.png", b"fake_image_data", "image/png")},
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == JobStatus.QUEUED.value
        app.state.rabbitmq_channel.default_exchange.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_accepts_heic(app):
    async with _client(app) as client:
        response = await client.post(
            "/upload",
            files={"files": ("camera.heic", b"fake_heic_data", "image/heic")},
        )
        assert response.status_code == 202
        assert response.json()["file_count"] == 1


@pytest.mark.asyncio
async def test_upload_rejects_non_image(app):
    async with _client(app) as client:
        response = await client.post(
            "/upload",
            files={"files": ("test.txt", b"text content", "text/plain")},
        )
        assert response.status_code == 400
        assert "content type" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_result_returns_404_for_unknown_job(app):
    async with _client(app) as client:
        response = await client.get("/result/nonexistent-job-id")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_result_returns_queued_status(app):
    await write_status("job-q", JobStatus.QUEUED, file_count=1)
    async with _client(app) as client:
        response = await client.get("/result/job-q")
        assert response.status_code == 202
        assert response.json()["status"] == JobStatus.QUEUED.value


@pytest.mark.asyncio
async def test_result_returns_completed_when_exists(app):
    await write_status("job-done", JobStatus.COMPLETED, file_count=1)
    result_path("job-done").write_text(json.dumps({"name": "John"}), encoding="utf-8")
    async with _client(app) as client:
        response = await client.get("/result/job-done")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.COMPLETED.value
        assert data["data"] == {"name": "John"}


@pytest.mark.asyncio
async def test_cancel_job_is_idempotent(app):
    async with _client(app) as client:
        response = await client.delete("/jobs/some-job-id")
        assert response.status_code == 200
        assert response.json()["status"] == JobStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_cancel_job_rejects_path_traversal(app):
    async with _client(app) as client:
        # Reaches the handler (no raw slash) but contains "..".
        response = await client.delete("/jobs/job..etc")
        assert response.status_code == 400
