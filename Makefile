.PHONY: install dev test lint typecheck run run-pdf run-api run-worker

install:
	uv sync

dev:
	uv pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy

run:
	uv run extract-data --input data/images/test_case_01

run-pdf:
	uv run extract-data --input data/pdf

run-api:
	uvicorn extractor.api.app:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	python -m extractor.worker.consumer