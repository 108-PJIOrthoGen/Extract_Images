FROM python:3.12-slim

WORKDIR /app
ENV BASE_DIR=/app

RUN pip install uv

COPY pyproject.toml README.md ./
COPY src/ src/
COPY templates/ templates/

RUN uv pip install --system --no-cache .

CMD ["extract-data"]
