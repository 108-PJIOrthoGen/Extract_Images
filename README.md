# Khai Thác Dữ Liệu Y Tế (Medical Result VLM Extractor)

Dự án này là một công cụ tự động trích xuất thông tin từ hình ảnh giấy tờ, phiếu kết quả khám bệnh hoặc hồ sơ y tế bằng cách sử dụng sức mạnh của Vision Language Model (VLM) thông qua OpenRouter API. Đầu ra là một luồng dữ liệu JSON đã được gán nhãn, chuẩn hoá dựa theo một mẫu (template) có sẵn.

## Các Tính Năng Góc
- **Đọc ảnh bằng VLM**: Sử dụng các mô hình ngôn ngữ lớn kết hợp thị giác (như Gemini 1.5 Pro, GPT-4o, Claude 3) để chuyển đổi từ ảnh quét kết quả xét nghiệm sang cấu trúc text.
- **Template-based Extraction**: Điền dữ liệu trực tiếp dựa trên một bộ khung `template.json` định sẵn. Các trường trống (thiếu dữ liệu) sẽ được tự động fill, trong khi đó các trường đã có dữ liệu hoặc khóa cố định sẽ được giữ nguyên.
- **Tự động vá lỗi định dạng đầu vào**: Hệ thống tự động biên dịch và làm sạch template do người dùng cập nhật thủ công nhằm đảm bảo JSON hợp lệ trước khi đẩy cho model.

## Yêu Cầu Cài Đặt

Dự án này sử dụng [uv](https://github.com/astral-sh/uv) kết hợp file cấu hình `pyproject.toml` để tối ưu hóa việc phân tích và cài đặt package.
Yêu cầu: `Python 3.8+`

1. Clone dự án từ Github và di chuyển vào thư mục gốc:
   ```bash
   git clone https://github.com/108-PJIOrthoGen/Extract_data_from_images.git
   cd Extract_data_from_images
   ```
2. Khởi tạo môi trường ảo và đảm bảo các dependency được cài đặt, đồng thời cài đặt project dưới local:
   ```bash
   # Đồng bộ thư viện trong pyproject.toml
   uv sync
   
   # Cài đặt project vào môi trường ở chế độ editable
   uv pip install -e .
   ```

## Cấu Hình API Key

Bạn cần cung cấp API key từ OpenRouter để VLM hoạt động. Copy file mẫu ra một bản `.env`:
```bash
cp .env.example .env
```
Mở file `.env` và gắn API key của bạn:
```env
OPENROUTER_API_KEY="your_api_key_here"
# Tùy chọn, thiết lập mô hình VLM. Mặc định là google/gemini-1.5-pro
OPENROUTER_MODEL="google/gemini-1.5-pro"
```

## Tổ Chức Thư Mục

Dưới đây là một sơ đồ kiến trúc thư mục chuẩn của hệ thống để bạn dễ dàng nắm bắt:

```text
Extract_data_from_images/
├── src/
│   └── extractor/               <- Package chính chứa source code
│       ├── core/                <- Chứa các nghiệp vụ (domain logic)
│       │   ├── image_loader.py  <- Xử lý tải ảnh và convert Base64
│       │   ├── template_parser.py <- Xử lý làm sạch và format JSON Schema
│       │   └── vlm_client.py    <- Class giao tiếp OpenRouter API
│       ├── utils/               
│       │   └── logger.py        <- Cấu hình Logging chung
│       ├── config.py            <- Lưu thiết lập cấu hình & biến môi trường
│       └── main.py              <- CLI Entry point
├── templates/
│   └── template.json            <- Cấu trúc chuẩn JSON cho OpenRouter 
├── tests/                       <- Nơi chứa Unit Tests
│   └── test_template_parser.py  <- Test kiểm duyệt JSON fixing
├── images/                      <- Thư mục chứa đầu vào
│   ├── test_case_01/            
│   └── test_case_02/            
├── outputs/                     <- Nơi tự động lưu JSON kết quả
├── .env.example                 <- File mẫu cho biến môi trường
├── .gitignore                   
├── LICENSE                      
├── README.md                    
└── pyproject.toml               <- Cấu hình PDM/uv, dependencies và Dev tools
```

## Hướng Dẫn Tải Ảnh (Upload Images) Đầu Vào

Hệ thống của dự án được thiết kế xử lý dữ liệu hồ sơ bệnh án theo *từng ca một* nhằm đảm bảo độ chính xác. Để nhúng ảnh vào hệ thống, bạn cần tuân theo trình tự sau:

1. **Tạo Phân Vùng Lữu Trữ**: Vào trong thư mục `images/` và tạo ra một folder mới, đặt tên tùy chọn đại diện cho bệnh nhân, mã hồ sơ hay ca test (ví dụ: `images/BN_NguyenVanA/` hoặc `images/test_case_05/`). 
2. **Upload/Copy Ảnh**: Hãy kéo thả, copy các ảnh giấy tờ, phiếu xét nghiệm lâm sàng, sổ khám bệnh,... đưa toàn bộ vào trong thư mục con vừa tạo của bạn. Các mức định dạng hệ thống chấp nhận là `.jpg`, `.jpeg`, `.png`.
3. **Thứ tự (Không Bắt Buộc nhưng Khuyến Khích)**: Mặc dù model VLM khá linh hoạt, bạn nên đánh số trang ảnh theo thứ tự xuất hiện của nó (ví dụ: `image_1.jpg`, `image_2.jpg`) giúp model tổng hợp thông tin liền mạch hơn. Tối đa của 1 lần gửi hãy giới hạn dưới số trang mà VLM của bạn được hỗ trợ.

## Cách Sử Dụng

Sử dụng thư viện `uv` để chạy script và trỏ tới thư mục chứa ảnh xét nghiệm của bạn:

```bash
# Lệnh dưới đây sẽ đọc toàn bộ ảnh trong thư mục images/test_case_01 và nhả kết quả tại outputs/test_case_01.json
uv run extract-data --input images/test_case_01
```

Nếu folder đầu vào của bạn khác, chỉ cần truyền lại cờ `--input`:
```bash
uv run extract-data --input path/to/your/image_folder
```

## Dành Cho Đội Ngũ Phát Triển (Handoff & Contributing)

Dự án đã được cấu trúc lại hoàn toàn theo chuẩn **src-layout** và tuân thủ **PEP8**. Các dependencies hỗ trợ môi trường phát triển đã được đóng gói thông qua công cụ tùy chọn `[project.optional-dependencies]`.

Để cài đặt môi trường dev và chạy Test:
1. Đảm bảo toàn bộ gói phát triển được nạp đúng cách:
```bash
uv pip install -e ".[dev]"
```
2. Chạy Unit Tests để xác minh thư viện parser cốt lõi bằng lệnh ngắn gọn `pytest`:
```bash
pytest
```
3. Kiểm tra tiêu chuẩn định dạng mã hóa và Linting bằng `ruff` (linter cực nhanh bằng Rust thay cho pre-commit cũ):
```bash
ruff check .
```

## Kiến Trúc Message Queue (Web App Integration)

Dự án hỗ trợ kiến trúc bất đồng bộ sử dụng RabbitMQ để web app có thể gửi ảnh cho team AI xử lý.

### Sơ Đồ Luồng Dữ Liệu

```
[Web App] --upload ảnh--> [FastAPI /upload] --message--> [RabbitMQ] --consume--> [Worker] --gọi VLM--> [Lưu JSON]
```

### Yêu Cầu

- RabbitMQ server đang chạy
- Cài đặt thêm dependencies:
```bash
uv sync
```

### Cấu Hình RabbitMQ

Thêm vào file `.env`:
```env
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=image_processing
```

### Cách Chạy

**1. Chạy API Server (nhận upload từ web app):**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Chạy Worker (xử lý ảnh từ queue):**
```bash
python -m worker.consumer
```

### API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/upload` | Upload ảnh, gửi vào queue |
| GET | `/result/{job_id}` | Lấy kết quả JSON theo template |
| GET | `/health` | Health check |

### Cách Gọi API từ Web App

```python
import requests

# Bước 1: Upload ảnh
url = "http://localhost:8000/upload"
files = {"file": open("image.jpg", "rb")}

response = requests.post(url, files=files)
result = response.json()
job_id = result["job_id"]
# Output: {"job_id": "uuid-here", "status": "queued", "message": "Image sent to processing queue"}

# Bước 2: Kiểm tra kết quả (poll)
result_url = f"http://localhost:8000/result/{job_id}"
result_response = requests.get(result_url)
result_data = result_response.json()
# Processing: {"job_id": "uuid", "status": "processing"}
# Completed: {"job_id": "uuid", "status": "completed", "data": {...JSON theo template...}}
```

Kết quả sẽ được lưu tại `outputs/{job_id}.json` sau khi worker xử lý xong.
