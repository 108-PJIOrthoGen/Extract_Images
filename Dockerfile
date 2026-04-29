FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev --no-project

COPY src/ src/
COPY templates/ templates/

CMD ["uv", "run", "extract-data"]