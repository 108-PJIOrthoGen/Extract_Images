UV_CACHE_DIR ?= .uv-cache
PYTHONPATH ?= src
API_HOST ?= 0.0.0.0
API_PORT ?= 8002
UV = UV_CACHE_DIR=$(UV_CACHE_DIR) uv
UV_RUN = UV_CACHE_DIR=$(UV_CACHE_DIR) PYTHONPATH=$(PYTHONPATH) uv run

.PHONY: install dev test lint typecheck run run-pdf run-api run-worker

install:
	$(UV) sync

dev:
	$(UV) pip install -e ".[dev]"

test:
	$(UV_RUN) pytest -v

lint:
	$(UV_RUN) ruff check .
	$(UV_RUN) ruff format --check .

typecheck:
	$(UV_RUN) mypy

run:
	$(UV_RUN) extract-data --input data/images/test_case_01

run-pdf:
	$(UV_RUN) extract-data --input data/pdf

run-api:
	$(UV_RUN) uvicorn extractor.api.app:app --host $(API_HOST) --port $(API_PORT) --reload

run-worker:
	$(UV_RUN) python -m extractor.worker.consumer
