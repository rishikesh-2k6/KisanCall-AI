# ============================================================
# config.py — Centralized Configuration for KisanCall AI
# ============================================================
# Loads environment variables and provides typed settings
# used across all modules.
# ============================================================

import os
from dotenv import load_dotenv

# Load .env file if present (development mode)
load_dotenv()

# ── Twilio ───────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER", "")  # Your personal number for testing

# ── Ollama (Local LLM) ──────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")

# ── Server ───────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# ── Open-Meteo (free, no key needed) ────────────────────
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
