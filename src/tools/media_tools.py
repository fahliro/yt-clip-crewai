"""CrewAI tools that wrap the yt-dlp / Groq Whisper / ffmpeg / YouTube-upload
pipeline. Each tool is a thin, agent-callable wrapper around the proven logic
from yt-clip-automation/clip.py."""
from __future__ import annotations

import json
import os
import re
import time
from typing import Dict, List

import requests
from crewai.tools import BaseTool

from ..utils import run, fmt_time, log, WORKDIR
from ..config import (
    GROQ_API_KEY, YT_COOKIES_TXT, YT_CHANNEL_ID,
    YT_UPLOAD_CLIENT, YT_UPLOAD_SECRET, YT_UPLOAD_TOKEN, YT_READ_TOKEN,
    SILENCE_GAP, DEFAULT_FILLERS,
)


# ------------------------------------------------------------------ download
class DownloadRawTool(BaseTool):
    name: str = "download_raw_video"
    description: str = (
        "Download a YouTube video to a local .mp4 given a video_id. "
        "YT_COOKIES_TXT is expected to be BASE64 of a Netscape cookies.txt "
        "(decoded to a temp file, then passed to yt-dlp --cookies). "
        "Returns the absolute path to the downloaded file."
    )

    def _run(self, video_id: str) -> str:
        from ..config import YT_COOKIES_TXT
        out = WORKDIR / f"{video_id}.mp4"
        cmd = ["yt-dlp", "-f", "best[height<=1080]",
               "--js-runtimes", os.environ.get("YTDLP_JS_RUNTIME", "node"),
               "--remote-components", "ejs:github",
               "-o", str(out), "--no-playlist"]
        if YT_COOKIES_TXT:
            import base64
            b64 = YT_COOKIES_TXT.strip()
            try:
                raw = base64.b64decode(b64).decode("utf-8")
            except Exception:
                raw = b64.replace("\r\n", "\n").replace("\r", "\n")
            raw = raw.replace("\r\n", "\n").replace("\r", "\n")
            cookies = WORKDIR / "cookies.txt"
            cookies.write_text(raw, newline="\n", encoding="utf-8")
            cmd += ["--cookies", str(cookies)]
        cmd.append(f"https://www.youtube.com/watch?v={video_id}")
        run(cmd)
        if not out.exists():
            raise RuntimeError("download gagal")
        log(f"download selesai: {out}")
        return str(out)


# -------------------------------------------------------------- transcribe
class TranscribeTool(BaseTool):
    name: str = "transcribe_audio"
    description: str = (
        "Transcribe an mp4 with Groq Whisper (verbose_json) and return a dict "
        "with 'duration' and 'words' (list of {word,start,end})."
    )

    def _run(self, video_path: str) -> Dict:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        with open(video_path, "rb") as f:
            r = requests.post(url,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": f},
                data={"model": "whisper-large-v3", "response_format": "verbose_json"},
                timeout=300)
        if not r.ok:
            log(f"[groq] HTTP {r.status_code}: {r.text[:500]}")
            r.raise_for_status()
        data = r.json()
        flat = [w for seg in data.get("segments", []) for w in seg.get("words", [])]
        log(f"[groq] flatten words dari segments: {len(flat)} kata")
        return {"duration": data.get("duration", 0), "words": flat}


# ------------------------------------------------------------- pick segments
class PickSegmentsTool(BaseTool):
    name: str = "pick_segments"
    description: str = (
        "Given a transcript dict {duration,words}, ask the chat LLM to choose the "
        "best 3-8 short-form segments. Returns a JSON list of "
        "{start,end,score,reason,fillers}."
    )

    def _run(self, transcript: Dict) -> List[Dict]:
        from crewai import LLM
        from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
        words = transcript.get("words", [])
        if not words:
            dur = float(transcript.get("duration") or 0)
            if dur <= 0:
                return [{"start": 0, "end": 0, "score": 5,
                         "reason": "fallback-no-words", "fillers": DEFAULT_FILLERS}]
            return [{"start": i, "end": min(i + 45, dur), "score": 5,
                     "reason": "fallback", "fillers": DEFAULT_FILLERS}
                    for i in range(0, int(dur), 45)]

        chunks, t, buf = [], 0.0, []
        for w in words:
            buf.append(w["word"])
            if w["end"] - t >= 5:
                chunks.append(f"[{t:.0f}s] " + " ".join(buf))
                t, buf = w["end"], []
        prompt = (
            "Kamu editor video short. Dari transkrip ber-timestamp berikut, pilih 3-8 segmen "
            "menarik untuk YouTube Shorts (30-60 detik). Untuk TIAP segmen berikan: "
            "start (detik), end (detik), score virality (1-10), reason singkat, dan "
            "fillers = array kata pengisi/pembuka tidak penting dalam segmen itu "
            "(mis: 'yah','gitu','eh','ya'). Jawab HANYA JSON array: "
            "[{\"start\":float,\"end\":float,\"score\":int,\"reason\":str,\"fillers\":[str]}].\n"
            + "\n".join(chunks)[:14000]
        )
        llm = LLM(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY, temperature=0.2)
        content = llm.call(messages=[
            {"role": "system", "content": "Output JSON saja tanpa markdown."},
            {"role": "user", "content": prompt},
        ])
        content = re.sub(r"```(?:json)?", "", content).strip().strip("`")
        try:
            segs = json.loads(content)
        except Exception:
            log(f"LLM gagal parse: {content[:400]}")
            segs = [{"start": i, "end": min(i + 45, words[-1]["end"]), "score": 5,
                     "reason": "fallback", "fillers": DEFAULT_FILLERS}
                    for i in range(0, int(words[-1]["end"]), 45)]
        for s in segs:
            s.setdefault("fillers", DEFAULT_FILLERS)
        segs.sort(key=lambda s: s.get("score", 0), reverse=True)
        log(f"LLM pilih {len(segs)} segmen")
        return segs


# ----------------------------------------------------------------- caption
class BuildCaptionTool(BaseTool):
    name: str = "build_caption_ass"
    description: str = (
        "Build an .ass subtitle file (Opus-style typographic captions: white bold, "
        "black outline, bottom-center) from a list of word dicts {word,start,end}. "
        "Returns the .ass path."
    )

    def _run(self, words: List[Dict], out_path: str) -> str:
        style = ("Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,1,0,0,0,100,100,0,0,2,20,20,20,1")
        lines = [
            "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
            "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            style, "", "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
        for w in words:
            s = fmt_time(w["start"]); e = fmt_time(w["end"])
            txt = w["word"].strip().replace(",", " ")
            lines.append(f"Dialogue: 0,{s},{e},Default,,0,0,0,,{txt}")
        Path(out_path).write_text("\n".join(lines), encoding="utf-8")
        return out_path


# ------------------------------------------------------------------- cut
def _build_ass(words, ass_path):
    BuildCaptionTool()._run(words, str(ass_path))


def _cut_span(raw_path, s, e, words, idx, i):
    from ..config import WORKDIR
    dur = max(0.5, e - s)
    out = WORKDIR / f"part_{idx:02d}_{i:02d}.mp4"
    ass = WORKDIR / f"cap_{idx:02d}_{i:02d}.ass"
    if words:
        _build_ass(words, ass)
        fc = (f"[0:v]scale=1080:-1,boxblur=20[bg];"
              f"[0:v]scale=1080:-1[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2[ov];"
              f"[ov]subtitles={ass},format=yuv420p[v]")
    else:
        fc = (f"[0:v]scale=1080:-1,boxblur=20[bg];"
              f"[0:v]scale=1080:-1[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    run(["ffmpeg", "-y", "-ss", f"{s:.2f}", "-i", str(raw_path), "-t", f"{dur:.2f}",
         "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-c:a", "aac", "-b:a", "128k", str(out)])
    return out


class CutClipTool(BaseTool):
    name: str = "cut_clip"
    description: str = (
        "Cut one segment from the raw video using its start/end and word-level "
        "timestamps (drops filler words + silence gaps, burns Opus-style captions). "
        "Args: raw_path, seg(dict with start/end/fillers), words(list), idx(int). "
        "Returns the final clip .mp4 path."
    )

    def _run(self, raw_path: str, seg: Dict, words: List[Dict], idx: int) -> str:
        from ..config import WORKDIR
        start, end = float(seg["start"]), float(seg["end"])
        fillers = set(w.lower() for w in seg.get("fillers", DEFAULT_FILLERS))
        seg_words = [w for w in words if start <= w["start"] < end]
        kept = [w for w in seg_words if w["word"].strip().lower() not in fillers]
        spans, cur = [], None
        for w in kept:
            if cur is None:
                cur = [w["start"], w["end"]]
            elif w["start"] - cur[1] <= SILENCE_GAP:
                cur[1] = w["end"]
            else:
                spans.append(cur); cur = [w["start"], w["end"]]
        if cur:
            spans.append(cur)
        if not spans:
            spans = [[start, end]]
            seg_words = [w for w in words if start <= w["start"] < end]
        parts = []
        for i, (s, e) in enumerate(spans):
            span_words = [w for w in seg_words if s <= w["start"] < e]
            parts.append(_cut_span(raw_path, s, e, span_words, idx, i))
        final = WORKDIR / f"clip_{idx:02d}.mp4"
        if len(parts) == 1:
            parts[0].rename(final)
        else:
            lst = WORKDIR / f"concat_{idx:02d}.txt"
            lst.write_text("\n".join(f"file '{p}'" for p in parts), encoding="utf-8")
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-c:a", "aac", "-b:a", "128k", str(final)])
        log(f"clip {idx} siap: {final}")
        return str(final)


# ------------------------------------------------------------------ upload
class UploadTool(BaseTool):
    name: str = "upload_youtube"
    description: str = (
        "Upload a clip .mp4 to YouTube (public) via the Upload API using the OAuth "
        "client credentials. Args: path, title, description. Returns the watch URL."
    )

    def _run(self, path: str, title: str, description: str) -> str:
        tok = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": YT_UPLOAD_CLIENT, "client_secret": YT_UPLOAD_SECRET,
            "refresh_token": YT_UPLOAD_TOKEN, "grant_type": "refresh_token",
        }).json()
        access = tok["access_token"]
        meta = json.dumps({
            "snippet": {"title": title[:100], "description": (description or "")[:4900],
                        "channelId": YT_CHANNEL_ID},
            "status": {"privacyStatus": "public"},
        }).encode()
        last_err = None
        for attempt in range(3):
            try:
                with open(path, "rb") as f:
                    r = requests.post(
                        "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=multipart",
                        headers={"Authorization": f"Bearer {access}"},
                        files={"metadata": ("meta", meta, "application/json; charset=UTF-8"),
                               "media": (Path(path).name, f, "video/*")},
                        timeout=600)
                    r.raise_for_status()
                vid = r.json()["id"]
                url = f"https://youtu.be/{vid}"
                log(f"uploaded: {url}")
                return url
            except requests.HTTPError as e:
                last_err = e
                body = ""
                try:
                    body = e.response.text[:400]
                except Exception:
                    pass
                log(f"[upload] attempt {attempt+1} gagal HTTP {e.response.status_code if e.response else '?'} body={body}")
                if e.response and e.response.status_code == 400:
                    time.sleep(20 * (attempt + 1)); continue
                raise
        raise last_err or RuntimeError("upload gagal")


# -------------------------------------------------------------- poll (cron)
class PollLatestTool(BaseTool):
    name: str = "poll_latest_video"
    description: str = (
        "Fallback: return the newest video_id on the channel via YouTube Data API "
        "(needs YT_READ_TOKEN, scope youtube.readonly). Returns video_id or None."
    )

    def _run(self) -> str | None:
        if not YT_READ_TOKEN:
            log("[poll] YT_READ_TOKEN kosong -> skip")
            return None
        t = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": YT_UPLOAD_CLIENT, "client_secret": YT_UPLOAD_SECRET,
            "refresh_token": YT_READ_TOKEN, "grant_type": "refresh_token",
        }).json()
        access = t.get("access_token")
        if not access:
            log("[poll] gagal token baca"); return None
        r = requests.get("https://www.googleapis.com/youtube/v3/search",
                         params={"channelId": YT_CHANNEL_ID, "part": "id",
                                 "order": "date", "maxResults": 1, "type": "video"},
                         headers={"Authorization": f"Bearer {access}", "Accept": "application/json"})
        r.raise_for_status()
        items = r.json().get("items", [])
        return items[0]["id"]["videoId"] if items else None
