.PHONY: install dev test lint run run-api run-worker

install:
	uv sync

dev:
	uv pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .
	ruff format --check .

run:
	uv run extract-data --input images/test_case_01

run-api:
	uvicorn extractor.api.app:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	python -m extractor.worker.consumer