import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUTS_DIR = BASE_DIR / "outputs"
UPLOAD_DIR = BASE_DIR / "uploads"

TEMPLATE_PATH = TEMPLATES_DIR / "template.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-1.5-pro")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "image_processing")

# API details
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Retry configuration for rate limiting
VLM_MAX_RETRIES = int(os.getenv("VLM_MAX_RETRIES", "5"))
VLM_BASE_DELAY = float(os.getenv("VLM_BASE_DELAY", "1.0"))
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
