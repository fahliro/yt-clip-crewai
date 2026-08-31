#!/usr/bin/env python3
"""
refresh_yt_cookies.py
- Login ke YouTube menggunakan Camoufox (anti-detect Firefox)
- Ekspor cookie ke format Netscape
- Output base64 string (siap untuk env var YT_COOKIES_TXT)

Environment variables required:
  YT_USERNAME      - Email akun YouTube
  YT_APP_PASSWORD  - App password (jika 2FA aktif) atau password biasa
"""
import base64
import os
import sys
import time
from pathlib import Path

try:
    from camoufox.sync_api import Camoufox
except Exception as e:
    sys.stderr.write(f"Gagal import Camoufox: {e}\n")
    sys.exit(1)


def main():
    username = os.getenv("YT_USERNAME")
    password = os.getenv("YT_APP_PASSWORD")
    if not username or not password:
        sys.stderr.write("Secret YT_USERNAME / YT_APP_PASSWORD belum di-set.\n")
        sys.exit(1)

    # Folder temporary untuk profile Camoufox (tiap run bersih)
    user_data_dir = Path.home() / "camoufox_tmp_yt"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    with Camoufox(headless=True, user_data_dir=str(user_data_dir)) as browser:
        page = browser.new_page()

        # Buka halaman login YouTube
        page.goto(
            "https://accounts.google.com/ServiceLogin?service=youtube&uilel=3&hl=id&continue=https://www.youtube.com/",
            wait_until="networkidle",
        )

        # Isi email
        page.fill('input[type="email"]', username)
        page.click("#identifierNext")
        page.wait_for_timeout(2000)

        # Isi password
        page.fill('input[type="password"]', password)
        page.click("#passwordNext")

        # Tunggu hingga kembali ke YouTube (atau muncul tantangan CAPTCHA)
        try:
            page.wait_for_url("https://www.youtube.com/**", timeout=30000)
        except Exception:
            # Cek apakah ada tantangan CAPTCHA
            if "challenge" in page.url or "suspicious" in page.url.lower():
                sys.stderr.write(
                    "Login terdeteksi CAPTCHA/tantangan keamanan. "
                    "Selesaikan manual sekali, lalu coba lagi.\n"
                )
                sys.exit(1)
            raise

        # Pastikan sudah login: cek adanya avatar/button akun
        try:
            page.wait_for_selector(
                "ytd-topbar-menu-button-renderer#avatar-btn", timeout=15000
            )
        except Exception:
            sys.stderr.write("Login gagal: avatar akun tidak ditemukan.\n")
            sys.exit(1)

        # Ekspor cookie ke format Netscape
        cookies = page.context.cookies()
        # Format Netscape: domain\tflag\tpath\tsecure\texpiration\tname\tvalue
        lines = ["# Netscape HTTP Cookie File"]
        for c in cookies:
            domain = c["domain"]
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = c["path"]
            secure = "TRUE" if c["secure"] else "FALSE"
            expiry = str(int(c["expires"])) if "expires" in c and c["expires"] else "0"
            name = c["name"]
            value = c["value"]
            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
        cookie_txt = "\n".join(lines) + "\n"

        # Base64-encode
        b64 = base64.b64encode(cookie_txt.encode("utf-8")).decode("ascii")
        # Hanya print ke stdout (akan ditangkap sebagai output step)
        print(b64)


if __name__ == "__main__":
    main()
