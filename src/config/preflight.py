"""Preflight: validate that the YouTube OAuth credentials can actually produce
a valid access token (STABLE path) AND/OR that cookies are usable. If both fail,
fail FAST with an explicit ACTION REQUIRED message instead of letting yt-dlp
silently report 'Private video' deep inside the pipeline."""

import os
import sys

from .settings import get_access_token  # relative import works when run as module


def main() -> int:
    bearer = get_access_token()
    if bearer:
        print("[preflight] OAuth access token OK (Bearer siap dipakai download+upload)")
        return 0

    # Bearer gagal -> coba cookies (fragile) sebagai fallback
    cookies_b64 = (os.environ.get("YT_COOKIES_TXT") or "").strip()
    if not cookies_b64:
        print("\n" + "=" * 70)
        print("ACTION REQUIRED: YT_UPLOAD_TOKEN (OAuth refresh token) GAGAL refresh,")
        print("dan YT_COOKIES_TXT kosong. Jalankan get_auth_token.py untuk re-consent")
        print("OAuth scope 'youtube' (download private + upload), lalu update secret")
        print("YT_UPLOAD_TOKEN di Environment YT_CHANNEL_ID. Atau isi YT_COOKIES_TXT.")
        print("=" * 70)
        return 1

    import base64, tempfile, subprocess
    raw = cookies_b64
    try:
        raw = base64.b64decode(cookies_b64).decode("utf-8")
    except Exception:
        raw = cookies_b64.replace("\r\n", "\n").replace("\r", "\n")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    cf.write(raw); cf.close()

    test_id = (os.environ.get("VIDEO_ID") or "YVLYNuhKZpc").strip()
    probe = ["yt-dlp", "-f", "best[height<=1080]",
             "--extractor-args", "youtube:player_client=web",
             "--cookies", cf.name, "--no-playlist", "-F",
             f"https://www.youtube.com/watch?v={test_id}"]
    print(f"[preflight] Bearer kosong; probing cookies fallback vs {test_id} ...")
    r = subprocess.run(probe, capture_output=True, text=True, timeout=120)
    out = r.stdout + "\n" + r.stderr
    if r.returncode != 0 and ("no longer valid" in out or "Private video" in out or "Sign in" in out):
        print("\n" + "=" * 70)
        print("ACTION REQUIRED: cookies EXPIRED/ROTATED. Re-consent OAuth via")
        print("get_auth_token.py (scope 'youtube') untuk jalur stabil, atau re-export")
        print("cookies Netscape .txt -> base64 -> update YT_COOKIES_TXT.")
        print("=" * 70)
        return 1
    print("[preflight] cookies fallback OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
