"""Central config. Loads .env (or GitHub Actions env vars) and builds the
CrewAI LLM from the SAME OpenAI-compatible endpoint used by yt-clip-automation
(LLM_API_KEY / LLM_BASE_URL / LLM_MODEL), plus Groq Whisper for transcription.
"""
from __future__ import annotations

import os
import requests
from pathlib import Path

from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

# ---- paths ----
ROOT = Path(__file__).resolve().parents[2]
WORKDIR = ROOT / "workdir"
WORKDIR.mkdir(exist_ok=True)

STATE_FILE = Path(os.environ.get("STATE_FILE", "state.json"))
if not STATE_FILE.is_absolute():
    STATE_FILE = ROOT / STATE_FILE

# ---- credentials ----
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "")
YT_COOKIES_TXT = os.environ.get("YT_COOKIES_TXT", "")
YT_UPLOAD_CLIENT = os.environ.get("YT_UPLOAD_CLIENT", "")
YT_UPLOAD_SECRET = os.environ.get("YT_UPLOAD_SECRET", "")
YT_UPLOAD_TOKEN = os.environ.get("YT_UPLOAD_TOKEN", "")
YT_READ_TOKEN = os.environ.get("YT_READ_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ---- LLM for agents (OpenAI-compatible, same as old repo) ----
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "")


def get_access_token() -> str | None:
    """Refresh the YouTube OAuth refresh token into a short-lived access token.

    Returns the access token string, or None if credentials are missing / the
    refresh fails. Used as a STABLE alternative to fragile browser cookies for
    downloading the owner's own private videos and for uploading.
    """
    if not (YT_UPLOAD_CLIENT and YT_UPLOAD_SECRET and YT_UPLOAD_TOKEN):
        return None
    try:
        r = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": YT_UPLOAD_CLIENT,
                "client_secret": YT_UPLOAD_SECRET,
                "refresh_token": YT_UPLOAD_TOKEN,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception as e:  # noqa: BLE001
        print(f"[auth] gagal refresh access token: {e}")
        return None


def build_llm(temperature: float = 0.2) -> LLM:
    """Build a CrewAI LLM bound to the OpenAI-compatible endpoint.

    If LLM_MODEL is empty we DO NOT pass model= (mirrors the old repo.py
    behaviour, where requests.post sent "model": "" and the endpoint used its
    own default). CrewAI requires a non-empty model string, so in that case we
    fall back to a harmless placeholder and let the endpoint override.
    """
    if not (LLM_API_KEY and LLM_BASE_URL):
        raise RuntimeError(
            "LLM_* tidak lengkap. Set LLM_API_KEY, LLM_BASE_URL "
            "(dan opsional LLM_MODEL) — sama seperti repo yt-clip-automation."
        )
    model = LLM_MODEL or "openai-compatible-default"
    return LLM(
        model=model,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=temperature,
    )


# sensible defaults reused from clip.py
SILENCE_GAP = 0.5          # detik; span terpisah > ini = dianggap jeda/silence
MAX_CLIPS = 5
MAX_SEGMENTS = 8
TEST_VIDEO_ID = os.environ.get("VIDEO_ID", "")
DEFAULT_FILLERS = ["yah", "gitu", "eh", "ya", "kayak", "anu", "hmm"]
