from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from extractor.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_upload_returns_202(app):
    with patch("extractor.api.routes.settings") as mock_settings:
        mock_settings.UPLOAD_DIR = MagicMock()
        mock_settings.UPLOAD_DIR.__truediv__ = MagicMock(return_value=MagicMock())
        mock_settings.RABBITMQ_QUEUE = "test_queue"

        with patch("aiofiles.open", new_callable=AsyncMock), patch("aio_pika.Message"):
            with patch("aio_pika.IncomingChannel") as mock_channel:
                mock_channel.default_exchange.publish = AsyncMock()

                mock_app_state = MagicMock()
                mock_app_state.rabbitmq_channel = mock_channel

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/upload",
                        files={"file": ("test.png", b"fake_image_data", "image/png")},
                    )

                    assert response.status_code == 202
                    data = response.json()
                    assert "job_id" in data
                    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_upload_rejects_non_image(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/upload",
            files={"file": ("test.txt", b"text content", "text/plain")},
        )
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_result_returns_processing_when_not_found(app):
    with patch("extractor.api.routes.settings") as mock_settings:
        mock_settings.OUTPUTS_DIR = MagicMock()
        mock_settings.OUTPUTS_DIR.__truediv__ = MagicMock(
            return_value=MagicMock(exists=MagicMock(return_value=False))
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/result/nonexistent-job-id")
            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_result_returns_completed_when_exists(app):
    with patch("extractor.api.routes.settings") as mock_settings:
        mock_output_path = MagicMock()
        mock_output_path.exists.return_value = True
        mock_settings.OUTPUTS_DIR.__truediv__ = MagicMock(return_value=mock_output_path)

        with patch("aiofiles.open", new_callable=AsyncMock) as mock_aiofiles:
            mock_file = AsyncMock()
            mock_file.read = AsyncMock(return_value='{"name": "John"}')
            mock_aiofiles.return_value.__aenter__.return_value = mock_file

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/result/test-job-id")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["data"] == {"name": "John"}
