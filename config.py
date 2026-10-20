"""
Ruta: config.py
Descripción: Configuración central unificada de Argon 4 // Hermes Edition (Google Gemini, Ollama,
Notion, IMAP, WhatsApp, Voz Grave y Telemetría JSON para Rainmeter/HUD).
"""
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

SKINS_DIR = BASE_DIR / "skins"
SKINS_DIR.mkdir(exist_ok=True)

TELEMETRY_FILE = LOG_DIR / "runtime_telemetry.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "agent_activity.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)


class Config:
    AGENT_NAME: str = os.getenv("AGENT_NAME", "Argon 4")
    LANGUAGE_CODE: str = os.getenv("LANGUAGE_CODE", "es-PE")
    ASSISTANT_VOICE: str = os.getenv("ASSISTANT_VOICE", "es-ES-AlvaroNeural")
    VOICE_PITCH: str = os.getenv("VOICE_PITCH", "-14Hz")
    VOICE_RATE_STR: str = os.getenv("VOICE_RATE", "+6%")
    VOICE_RATE: int = 175
    VOICE_VOLUME: float = float(os.getenv("VOICE_VOLUME", "1.0"))
    REQUIRE_CONFIRMATION: bool = os.getenv("REQUIRE_CONFIRMATION", "false").lower() == "true"

    # Motores Cognitivos (Google Gemini Principal + Ollama Local de Respaldo)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "45"))

    # Notion API
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "").strip()
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "").strip()

    # Canales: Correo IMAP, WhatsApp y VoIP
    EMAIL_IMAP_HOST: str = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
    EMAIL_USER: str = os.getenv("EMAIL_USER", "framenhig@gmail.com").strip()
    EMAIL_APP_PASSWORD: str = os.getenv("EMAIL_APP_PASSWORD", "").strip()

    _raw_cc = os.getenv("DEFAULT_COUNTRY_CODE", "+51").strip().split()[0]
    DEFAULT_COUNTRY_CODE: str = _raw_cc if _raw_cc.startswith("+") else "+51"
    DEFAULT_TARGET_PHONE: str = os.getenv("DEFAULT_TARGET_PHONE", "+51978552756").strip()

    WHATSAPP_BRIDGE_URL: str = os.getenv("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000")
    WHATSAPP_SESSION: str = os.getenv("WHATSAPP_SESSION", "argon_session")
    SIP_SOFTPHONE_BIN: str = os.getenv("SIP_SOFTPHONE_BIN", "linphonecsh")

    HUD_PORT: int = int(os.getenv("HUD_PORT", "8765"))


_telemetry_lock = threading.Lock()
_last_telemetry_signature = ""


def write_telemetry_snapshot(state: str, active_tool: str, last_action: str) -> None:
    """Guarda el estado instantáneo del agente en disco solo cuando cambia."""
    global _last_telemetry_signature
    clean_action = last_action[:150]
    sig = f"{state}|{active_tool}|{clean_action}"

    with _telemetry_lock:
        if sig == _last_telemetry_signature:
            return
        _last_telemetry_signature = sig
        payload: Dict[str, Any] = {
            "status": state,
            "tool": active_tool,
            "last_action": clean_action,
            "updated_at": datetime.now().strftime("%H:%M:%S"),
        }
        try:
            TELEMETRY_FILE.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass