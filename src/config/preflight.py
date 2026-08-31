"""Preflight: validate that the YouTube cookies can actually download the owner's
PRIVATE video (yt-dlp download REQUIRES cookies; OAuth Bearer only works for the
upload API). Fail FAST with an explicit ACTION REQUIRED message instead of letting
yt-dlp silently report 'Private video' deep inside the pipeline."""

import os
import sys

from .settings import get_access_token  # relative import works when run as module


def main() -> int:
    # Bearer is needed for the UPLOAD step (YouTube Data API), not download.
    bearer = get_access_token()
    if bearer:
        print("[preflight] OAuth Bearer OK (untuk upload API)")
    else:
        print("[preflight] Bearer KOSONG — upload bakal gagal. Re-consent via get_auth_token.py")

    cookies_b64 = (os.environ.get("YT_COOKIES_TXT") or "").strip()
    if not cookies_b64:
        print("\n" + "=" * 70)
        print("ACTION REQUIRED: YT_COOKIES_TXT kosong. Download video PRIVATE butuh")
        print("cookies yt-dlp. Export Netscape .txt dari youtube.com -> base64 ->")
        print("update secret YT_COOKIES_TXT di Environment YT_CHANNEL_ID.")
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
    print(f"[preflight] probing cookies vs {test_id} ...")
    r = subprocess.run(probe, capture_output=True, text=True, timeout=120)
    out = r.stdout + "\n" + r.stderr
    if r.returncode != 0 and ("no longer valid" in out or "Private video" in out or "Sign in" in out):
        print("\n" + "=" * 70)
        print("ACTION REQUIRED: cookies EXPIRED/ROTATED. Re-export cookies Netscape")
        print(".txt dari youtube.com -> base64 -> update YT_COOKIES_TXT.")
        print("=" * 70)
        return 1
    print("[preflight] cookies OK (download private video siap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
