"""
Central config — loads environment variables from .env at startup.
Canonical location: backend/core/config.py
"""
import os
from dotenv import load_dotenv

# Load .env from project root
_env_paths = [
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    ".env",
]
for _p in _env_paths:
    if os.path.exists(_p):
        load_dotenv(_p)
        break
else:
    load_dotenv()  # fallback: search CWD

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError(
        "\n" + "="*80 + "\n"
        "❌ GROQ_API_KEY is not set!\n\n"
        "Setup instructions:\n"
        "1. Copy the example file:    cp .env.example .env\n"
        "2. Get your Groq API key:    https://console.groq.com/keys\n"
        "3. Add it to .env:           GROQ_API_KEY=gsk_your_actual_key\n"
        "4. Restart the application\n"
        + "="*80
    )

# Optional — only required when DB tools are active
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Optional — only required when RAG is active
PDF_PATH = os.getenv("PDF_PATH")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Email
MAIL_SENDER       = os.getenv("MAIL_SENDER", "")
MAIL_APP_PASSWORD = os.getenv("MAIL_APP_PASSWORD", "")
