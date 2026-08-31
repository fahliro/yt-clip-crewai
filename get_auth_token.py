#!/usr/bin/env python3
"""
get_auth_token.py - Generate YouTube Data API OAuth refresh_token dengan scope
PENUH (youtube + youtube.upload) supaya SATU token bisa:
  - download video PRIVATE milik channel kamu sendiri (via yt-dlp --add-header Bearer)
  - upload video (via YouTube Data API)

Ini menggantikan cookies Netscape yang sering ROTATE/EXPIRE (fragile).

Cara pakai (di mesin kamu, BUKAN CI):
  1. Google Cloud Console:
       - enable "YouTube Data API v3"
       - OAuth consent screen -> publish (atau add test user = akun kamu)
       - Credentials -> Create OAuth Client ID -> type "Desktop app"
       - copy Client ID + Client Secret
  2. Jalankan (params, gak perlu edit file):
       python get_auth_token.py --client-id "....apps.googleusercontent.com" --client-secret "...."
  3. Browser buka URL, login akun PEMILIK channel, klik Izinkan.
  4. Paste "code" -> script print refresh_token.
  5. Masukkan 3 nilai ke GitHub Secrets (Environment YT_CHANNEL_ID):
       YT_UPLOAD_CLIENT = client_id
       YT_UPLOAD_SECRET = client_secret
       YT_UPLOAD_TOKEN  = refresh_token   <-- dipakai juga buat download + upload

Setelah ini, YT_COOKIES_TXT jadi OPSIONAL (fallback saja).
"""
import sys, json, argparse, urllib.parse, urllib.request, webbrowser

REDIRECT = "urn:ietf:wg:oauth:2.0:oob"
# PENUH: bisa read (download private) + upload
SCOPE = ("https://www.googleapis.com/auth/youtube "
         "https://www.googleapis.com/auth/youtube.upload")


def build_auth_url(client_id):
    p = {
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(p)


def exchange(client_id, client_secret, code):
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT,
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(urllib.request.urlopen(req))


def main():
    ap = argparse.ArgumentParser(description="Generate YouTube OAuth refresh_token (scope youtube + youtube.upload)")
    ap.add_argument("--client-id", required=True, help="OAuth Client ID (Desktop app)")
    ap.add_argument("--client-secret", required=True, help="OAuth Client Secret")
    args = ap.parse_args()
    client_id, client_secret = args.client_id, args.client_secret
    url = build_auth_url(client_id)
    print("\nBuka URL ini di browser (login akun PEMILIK channel), lalu copy 'code':\n")
    print(url, "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    code = input("Paste code di sini: ").strip()
    tok = exchange(client_id, client_secret, code)
    print("\n=== HASIL (masukkan ke GitHub Secrets Environment YT_CHANNEL_ID) ===")
    print("YT_UPLOAD_CLIENT  =", client_id)
    print("YT_UPLOAD_SECRET  =", client_secret)
    print("YT_UPLOAD_TOKEN   =", tok.get("refresh_token"))


if __name__ == "__main__":
    main()
