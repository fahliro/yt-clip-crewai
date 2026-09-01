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


# ---------- helpers ----------

def log(msg):
    """Cetak ke stderr agar tidak tercampur dengan output base64."""
    sys.stderr.write(f"[refresh_yt_cookies] {msg}\n")
    sys.stderr.flush()


def safe_fill(page, selector, value, timeout=60000, label="field"):
    """Isi input dengan retry: tunggu muncul, klik, fill."""
    log(f"Menunggu {label} ({selector})…")
    page.wait_for_selector(selector, state="visible", timeout=timeout)
    # Bersihkan dulu kalau ada nilai residual
    try:
        page.fill(selector, "")
    except Exception:
        pass
    page.fill(selector, value)
    log(f"{label} terisi.")


def safe_click(page, selector, timeout=60000, label="button"):
    log(f"Menunggu {label} ({selector})…")
    page.wait_for_selector(selector, state="visible", timeout=timeout)
    page.click(selector)
    log(f"{label} diklik.")


def wait_for_login_complete(page, timeout=60000):
    """Tunggu redirect kembali ke YouTube ATAU muncul CAPTCHA."""
    log("Menunggu navigasi setelah submit…")
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        url = page.url.lower()
        if "youtube.com" in url and "accounts.google.com" not in url:
            return
        if "challenge" in url or "signin/v2/identifier" in url or "/v3/signin" in url:
            # Tantangan 2FA / verifikasi
            log(f"Tantangan keamanan terdeteksi pada URL: {page.url}")
            sys.stderr.write(
                "Login butuh tantangan (2FA/verifikasi). "
                "Selesaikan manual atau gunakan App Password yang valid.\n"
            )
            sys.exit(1)
        time.sleep(1)
    raise TimeoutError(f"Timeout {timeout}ms menunggu redirect ke youtube.com (saat ini: {page.url})")


def verify_logged_in(page, timeout=30000):
    """Pastikan benar-benar login: cek ada avatar button di YouTube."""
    log("Verifikasi login (avatar YouTube)…")
    try:
        page.wait_for_selector(
            "ytd-topbar-menu-button-renderer#avatar-btn",
            state="visible",
            timeout=timeout,
        )
        log("Avatar ditemukan: login sukses.")
    except Exception:
        # Fallback: cek cookie LOGIN_INFO atau SID di storage
        cookies = page.context.cookies()
        has_session = any(
            c["name"] in ("LOGIN_INFO", "SID", "__Secure-1PSID", "__Secure-3PSID")
            for c in cookies
        )
        if has_session:
            log("Avatar tidak muncul, tapi cookie sesi ada. Lanjut.")
        else:
            log("Login gagal: avatar tidak ada & cookie sesi kosong.")
            sys.exit(1)


def export_netscape(cookies):
    """Konversi list cookie Playwright -> format Netscape."""
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c["domain"]
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c["path"]
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        # expires di Playwright bisa float (unix seconds) atau -1
        exp = c.get("expires")
        if exp is None or exp < 0:
            expiry = "0"
        else:
            expiry = str(int(exp))
        name = c["name"]
        value = c["value"]
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
    return "\n".join(lines) + "\n"


# ---------- main ----------

def main():
    username = os.getenv("YT_USERNAME")
    password = os.getenv("YT_APP_PASSWORD")
    if not username or not password:
        sys.stderr.write("Secret YT_USERNAME / YT_APP_PASSWORD belum di-set.\n")
        sys.exit(1)

    log("Membuka Camoufox (headless)…")
    with Camoufox(
        headless=True,
        ff_version=152,
        i_know_what_im_doing=True,
        os="windows",
        locale=["id-ID", "id"],
    ) as browser:
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
        )
        page = context.new_page()

        login_url = (
            "https://accounts.google.com/ServiceLogin"
            "?service=youtube&uilel=3&hl=id"
            "&continue=https://www.youtube.com/"
        )
        log(f"Membuka halaman login: {login_url}")
        page.goto(login_url, wait_until="domcontentloaded", timeout=60000)

        # Tangani interstitial consent "Before you continue to YouTube" jika muncul
        try:
            page.wait_for_selector("button:has-text('Continue')", timeout=5000)
            log("Halaman consent muncul, klik Continue…")
            page.click("button:has-text('Continue')")
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass  # Tidak ada interstitial, lanjut

        # Step 1: email
        safe_fill(page, 'input[type="email"]', username, label="email")
        safe_click(page, "#identifierNext", label="identifierNext")
        page.wait_for_load_state("networkidle", timeout=30000)

        # Step 2: password (mungkin selector berbeda di flow baru)
        pwd_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[aria-label*="Password"]',
        ]
        pwd_filled = False
        for sel in pwd_selectors:
            try:
                safe_fill(page, sel, password, timeout=15000, label="password")
                pwd_filled = True
                break
            except Exception:
                continue
        if not pwd_filled:
            log("Kolom password tidak ditemukan di semua selector kandidat.")
            sys.exit(1)

        # Tombol submit password
        for sel in ["#passwordNext", "#submit", 'button[type="submit"]']:
            try:
                safe_click(page, sel, timeout=10000, label="passwordNext")
                break
            except Exception:
                continue

        # Tunggu redirect
        wait_for_login_complete(page, timeout=60000)

        # Verifikasi login berhasil
        verify_logged_in(page, timeout=30000)

        # Kumpulkan cookie YouTube + Google
        log("Mengambil cookies…")
        cookies = page.context.cookies()
        # Filter hanya yang relevan untuk yt-dlp (YouTube + Google)
        keep = ("youtube.com", "google.com", ".youtube.com", ".google.com")
        relevant = [c for c in cookies if any(k in c["domain"] for k in keep)]
        log(f"Total cookies: {len(cookies)} (relevan: {len(relevant)})")

        if not relevant:
            sys.stderr.write("Tidak ada cookie yang berhasil dikumpulkan.\n")
            sys.exit(1)

        # Validasi minimal: harus ada minimal salah satu cookie sesi
        session_cookies = {
            "LOGIN_INFO",
            "SID",
            "__Secure-1PSID",
            "__Secure-3PSID",
            "HSID",
            "SSID",
            "APISID",
            "SAPISID",
        }
        found = {c["name"] for c in relevant} & session_cookies
        if not found:
            sys.stderr.write(
                f"Cookie sesi tidak ditemukan (mencari: {session_cookies}). "
                "Login mungkin gagal.\n"
            )
            sys.exit(1)
        log(f"Cookie sesi ditemukan: {sorted(found)}")

        cookie_txt = export_netscape(relevant)
        b64 = base64.b64encode(cookie_txt.encode("utf-8")).decode("ascii")
        log(f"Base64 length: {len(b64)} chars")
        # Output hanya base64 ke stdout (ditangkap workflow)
        print(b64)


if __name__ == "__main__":
    main()
