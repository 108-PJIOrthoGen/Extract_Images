# Medical Result VLM Extractor

Dự án này là công cụ tự động trích xuất thông tin từ hình ảnh giấy tờ, phiếu kết quả khám bệnh hoặc hồ sơ y tế bằng Vision Language Model (VLM) thông qua OpenRouter API.

## Tính Năng
- **VLM Extraction**: Sử dụng Gemini 1.5 Pro, GPT-4o, Claude 3 để chuyển đổi ảnh xét nghiệm sang JSON
- **Template-based**: Điền dữ liệu theo `template.json` định sẵn
- **Auto-retry**: Tự động retry khi VLM trả về JSON không hợp lệ
- **Async Processing**: Hỗ trợ RabbitMQ queue cho web app integration

## Yêu Cầu
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended)

## Cài Đặt

```bash
# Clone và cd vào thư mục
git clone https://github.com/108-PJIOrthoGen/Extract_data_from_images.git
cd Extract_data_from_images

# Cài đặt dependencies
uv sync
pip install -e .
```

## Cấu Hình

Copy `.env.example` thành `.env` và thêm API key:
```env
OPENROUTER_API_KEY="your_api_key_here"
OPENROUTER_MODEL="google/gemini-1.5-pro"
```

## Tổ Chức Thư Mục

```
Extract_data_from_images/
├── src/extractor/               # Main package
│   ├── api/                     # FastAPI application
│   │   ├── app.py              # App factory + lifespan
│   │   └── routes.py           # API endpoints
│   ├── clients/                 # External API clients
│   │   └── vlm_client.py        # OpenRouter VLM client
│   ├── core/                    # Domain logic
│   │   ├── extractor.py        # ExtractionPipeline orchestrator
│   │   ├── prompt_builder.py   # Prompt construction
│   │   ├── response_validator.py # Validation logic
│   │   └── template_parser.py  # Template parsing
│   ├── loaders/                 # Input adapters
│   │   └── image_loader.py     # Image loading & Base64 encoding
│   ├── models/                  # Pydantic schemas
│   │   └── template.py         # Template validation
│   ├── worker/                  # RabbitMQ consumer
│   │   └── consumer.py         # Async message consumer
│   ├── utils/
│   │   └── logger.py           # Logging configuration
│   ├── config.py               # Settings with validation
│   ├── exceptions.py           # Exception hierarchy
│   └── main.py                 # CLI entry point
├── tests/                       # Unit tests
├── templates/
│   └── template.json           # JSON template
├── images/                      # Input images
├── outputs/                    # Output JSON files
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Cách Sử Dụng

### CLI (Command Line)
```bash
# Chạy với thư mục ảnh mặc định
uv run extract-data --input images/test_case_01

# Tùy chọn thêm
uv run extract-data --input images/test_case_01 --output custom_output.json
uv run extract-data --input images/test_case_01 --max-retries 3
```

### Sử dụng Makefile (Recommended)
```bash
make install      # Cài đặt dependencies
make dev         # Cài đặt dev dependencies
make run         # Chạy CLI
make run-api     # Chạy FastAPI server
make run-worker  # Chạy RabbitMQ worker
make test        # Chạy tests
make lint        # Kiểm tra code style
```

### Docker
```bash
docker-compose up --build
```

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/upload` | Upload 1 hoặc nhiều ảnh, gửi vào queue |
| GET | `/result/{job_id}` | Lấy kết quả JSON theo job_id |
| GET | `/health` | Health check |

### Upload Ảnh
```bash
# Upload 1 ảnh
curl -X POST http://localhost:8000/upload \
  -F "files=@image.jpg"

# Upload nhiều ảnh
curl -X POST http://localhost:8000/upload \
  -F "files=@page1.jpg" \
  -F "files=@page2.jpg"
```

### Kiểm Tra Kết Quả
```bash
# Poll kết quả
curl http://localhost:8000/result/{job_id}

# Response khi đang xử lý:
# {"job_id": "...", "status": "processing"}

# Response khi hoàn thành:
# {"job_id": "...", "status": "completed", "data": {...}}
```

## RabbitMQ Configuration

Thêm vào `.env`:
```env
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=image_processing
```

## Development

```bash
# Cài đặt dev dependencies
pip install -e ".[dev]"

# Chạy tests
pytest -v

# Chạy lint
ruff check .
ruff format --check .

# Pre-commit hooks
pre-commit install
```

## Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[CLI: extract-data]
        WEB[Web App / API Client]
    end

    subgraph "API Layer"
        API[FastAPI: extractor.api.app]
        UPLOAD[POST /upload]
        RESULT[GET /result]
    end

    subgraph "Message Queue"
        MQ[RabbitMQ]
        QUEUE[Queue: image_processing]
    end

    subgraph "Worker Layer"
        WORKER[Worker: extractor.worker.consumer]
    end

    subgraph "Core Processing"
        LOADER[Image Loader]
        TEMPLATE[Template Parser]
        BUILDER[Prompt Builder]
        VLM[OpenRouter VLM Client]
        VALIDATOR[Response Validator]
        PIPELINE[ExtractionPipeline]
    end

    subgraph "Storage"
        UPLOAD_DIR[uploads/]
        OUTPUTS[outputs/*.json]
    end

    %% CLI Flow
    CLI --> LOADER
    CLI --> TEMPLATE
    CLI --> PIPELINE
    PIPELINE --> VLM
    VLM --> OUTPUTS

    %% API Flow
    WEB --> UPLOAD
    UPLOAD --> UPLOAD_DIR
    UPLOAD --> MQ
    MQ --> QUEUE
    QUEUE --> WORKER
    WORKER --> LOADER
    WORKER --> TEMPLATE
    WORKER --> PIPELINE
    PIPELINE --> VLM
    WORKER --> OUTPUTS
    WEB --> RESULT
    RESULT --> OUTPUTS
```

### Luồng Xử Lý Chi Tiết

```mermaid
sequenceDiagram
    participant Client as Client/API
    participant API as FastAPI
    participant MQ as RabbitMQ
    participant Worker as Worker
    participant VLM as OpenRouter
    participant FS as File System

    Note over Client,VLM: CLI Mode hoặc API Mode

    %% CLI Mode
    Client->>FS: Đọc ảnh từ images/
    FS-->>Client: Trả ảnh
    
    %% API Mode  
    Client->>API: POST /upload (files)
    API->>FS: Lưu ảnh vào uploads/
    API->>MQ: Publish message
    
    MQ->>Worker: Consume message
    
    Note over Worker,VLM: Worker xử lý (cả 2 mode)
    
    Worker->>FS: Đọc ảnh
    Worker->>FS: Đọc template.json
    Worker->>VLM: Gọi API với prompt + ảnh
    
    loop Retry Logic (max_retries)
        VLM-->>Worker: Response JSON
        Worker->>Worker: Validate JSON vs template
        alt JSON không hợp lệ
            Worker->>VLM: Retry với error context
        else JSON hợp lệ
            break
        end
    end
    
    Worker->>FS: Lưu kết quả outputs/{job_id}.json
    
    %% API Mode - Lấy kết quả
    Client->>API: GET /result/{job_id}
    API->>FS: Đọc outputs/{job_id}.json
    API-->>Client: Trả kết quả JSON
```

## License

[MIT](LICENSE)