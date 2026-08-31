"""Shared helpers ported verbatim from yt-clip-automation/clip.py so the agent
tools behave identically to the old single-script pipeline."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .settings import STATE_FILE, WORKDIR

LOG_PATH = WORKDIR / "run.log"


def log(msg: str) -> None:
    line = f"[yt-clip-crewai] {msg}"
    print(line)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd: list[str]) -> None:
    """Run a subprocess, raising on non-zero exit."""
    log("CMD " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(WORKDIR))


def fmt_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


# ---------------- state (anti double-clip) ----------------
def already_done(video_id: str) -> bool:
    if not STATE_FILE.exists():
        return False
    return video_id in set(json.loads(STATE_FILE.read_text()).get("done", []))


def mark_done(video_id: str) -> None:
    data = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"done": []}
    data.setdefault("done", [])
    if video_id not in data["done"]:
        data["done"].append(video_id)
    STATE_FILE.write_text(json.dumps(data))
