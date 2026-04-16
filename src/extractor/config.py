import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Configuration variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-1.5-pro")

# Specific paths
TEMPLATE_PATH = TEMPLATES_DIR / "template.json"

# API details
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
