"""
One-off script: list available Groq models.
Canonical location: backend/scripts/test_models.py
"""
import os
import requests

try:
    import backend.core.config as _cfg  # noqa: F401
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    import backend.core.config as _cfg  # noqa: F401

api_key = os.environ.get("GROQ_API_KEY")
url     = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type":  "application/json",
}

response = requests.get(url, headers=headers)
print(response.json())
