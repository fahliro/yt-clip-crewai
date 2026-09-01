# yt-clip-crewai — Setup Guide

## Arsitektur (Setelah Best-Practice Refactor)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. LOKAL (laptop) atau SELF-HOSTED RUNNER                      │
│     ↓ login YouTube via Camoufox (IP residential)               │
│     ↓ simpan cookies ke GitHub Secret YT_COOKIES_TXT           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. GITHUB ACTIONS (ubuntu-latest)                              │
│     ↓ decode YT_COOKIES_TXT dari secret                         │
│     ↓ download video private via yt-dlp                         │
│     ↓ CrewAI pipeline: transcribe → clip → upload               │
└─────────────────────────────────────────────────────────────────┘
```

## Kenapa Tidak Login di CI Lagi?

Google **membatasi login dari IP datacenter** (GitHub Actions). Percobaan dengan
Camoufox di runner publik selalu memicu halaman verifikasi/CAPTCHA. Solusi
terbaik: **login dari IP residential (lokal atau self-hosted runner)**.

## Opsi Setup

### Opsi A: Login Manual dari Laptop (Paling Simpel)

1. **Edit file `scripts/yt-cookies-refresh.bat`**
   - Ganti `YT_USERNAME` & `YT_APP_PASSWORD` (atau set env var global)
   - App Password bisa dibuat di https://myaccount.google.com/apppasswords

2. **Double-click `scripts\yt-cookies-refresh.bat`**
   - Tunggu ~30 detik sampai Camoufox selesai login
   - File base64 tersimpan di `%TEMP%\yt_cookies.b64`

3. **Upload ke GitHub Secret**
   - Buka https://github.com/fahliro/yt-clip-crewai/settings/secrets/actions
   - Klik environment **YT_CHANNEL_ID**
   - Edit secret **YT_COOKIES_TXT** → paste isi `.b64` (1 baris)

4. **Jadwalkan refresh manual setiap ~30 hari** (saat cookies expire)
   - Workflow `crew.yml` akan otomatis pakai secret tersebut

### Opsi B: Self-Hosted Runner (Full Otomatis)

1. **Daftarkan runner di rumah** (PC/laptop yang selalu nyala)
   - Ikuti: https://docs.github.com/en/actions/hosting-your-own-runners
   - Jalankan `./run.sh` di Linux atau `run.cmd` di Windows
   - Label default: `self-hosted`, `linux`, `X64`

2. **Buat PAT untuk update secret**
   - https://github.com/settings/tokens/new
   - Scope: `repo` (full control)
   - Simpan sebagai secret `REPO_PAT` di environment YT_CHANNEL_ID

3. **Aktifkan workflow `refresh-cookies.yml`**
   - Schedule: setiap Minggu jam 00:00 UTC
   - Workflow akan login → update secret → verifikasi

## Secrets yang Diperlukan

| Secret | Digunakan oleh | Sumber |
|---|---|---|
| `YT_USERNAME` | refresh-cookies | Email akun YouTube |
| `YT_APP_PASSWORD` | refresh-cookies | App Password Google (myaccount.google.com/apppasswords) |
| `YT_COOKIES_TXT` | crew.yml | Base64 dari `yt_cookies.b64` (diperbarui tiap ~30 hari) |
| `REPO_PAT` | refresh-cookies | Personal Access Token (untuk `gh secret set`) |
| `YT_CHANNEL_ID` | crew.yml | ID channel YouTube target |
| `YT_UPLOAD_CLIENT` | crew.yml | OAuth client_id untuk upload |
| `YT_UPLOAD_SECRET` | crew.yml | OAuth client_secret |
| `YT_UPLOAD_TOKEN` | crew.yml | OAuth refresh_token |
| `YT_READ_TOKEN` | crew.yml | (opsional) token untuk read API |
| `GROQ_API_KEY` | crew.yml | API key Groq (Whisper transcription) |
| `LLM_API_KEY` | crew.yml | LLM OpenAI-compatible |
| `LLM_BASE_URL` | crew.yml | Endpoint LLM (mis. OpenRouter) |

## Variabel

| Variable | Fungsi |
|---|---|
| `LLM_MODEL` | Model name, mis. `tencent/hy3:free` |

## Workflows

| File | Fungsi |
|---|---|
| `crew.yml` | Pipeline utama (download → crew → upload). Trigger: schedule, repository_dispatch, manual |
| `refresh-cookies.yml` | Auto-refresh cookies via self-hosted runner. Trigger: schedule (Minggu), manual |
| `setup-camoufox.yml` | Cache binary Camoufox (untuk testing/debug) |
| `test-camoufox.yml` | Test login & download, untuk debugging |

## Troubleshooting

**Login gagal di CI**: Pastikan Anda tidak menjalankan `refresh_yt_cookies.py` di
runner `ubuntu-latest` (publik). Gunakan self-hosted runner atau laptop.

**Cookies kadaluarsa**: Workflow `crew.yml` akan gagal di step
`Preflight - cek cookies YouTube masih valid`. Jalankan ulang
`scripts/yt-cookies-refresh.bat` atau trigger `refresh-cookies` secara manual.

**App Password tidak bisa**: Pastikan 2FA aktif dan App Password dibuat untuk
aplikasi "Mail / Other".
