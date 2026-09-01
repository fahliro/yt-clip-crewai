@echo off
REM ============================================================
REM  yt-cookies-refresh.bat
REM  Login YouTube di laptop & simpan base64 ke Temp.
REM  Output: C:\Users\Robby\AppData\Local\Temp\yt_cookies.b64
REM
REM  CARA PAKAI:
REM    1. Set env YT_USERNAME & YT_APP_PASSWORD
REM       (atau edit file ini langsung, baris 12-13)
REM    2. Double-click file ini
REM    3. Tunggu sampai Camoufox selesai login (~30 detik)
REM    4. Copy isi yt_cookies.b64 ke GitHub Secret YT_COOKIES_TXT
REM ============================================================

REM === Set credentials (opsional; hapus jika pakai env var global) ===
set "YT_USERNAME=fahli.robbya@gmail.com"
set "YT_APP_PASSWORD=YOUR_APP_PASSWORD_HERE"

REM === Pindah ke direktori repo ===
cd /d "C:\Users\Robby\yt-clip-crewai"

echo === Installing dependencies (jika belum) ===
python -m pip install -U --quiet camoufox
python -m camoufox fetch --quiet

echo.
echo === Logging in to YouTube ===
python .github\scripts\refresh_yt_cookies.py > "%TEMP%\yt_cookies.b64"
if errorlevel 1 (
    echo.
    echo [GAGAL] Login tidak berhasil. Periksa YT_USERNAME / YT_APP_PASSWORD.
    echo Atau jalankan di mode non-headless: edit script lalu set headless=False
    pause
    exit /b 1
)

echo.
echo === Cookie tersimpan: %TEMP%\yt_cookies.b64 ===
echo Ukuran: %~z...yt_cookies.b64% bytes
echo.
echo === LANGKAH SELANJUTNYA ===
echo 1. Buka https://github.com/fahliro/yt-clip-crewai/settings/secrets/actions
echo 2. Edit secret YT_COOKIES_TXT di environment YT_CHANNEL_ID
echo 3. Paste isi file %TEMP%\yt_cookies.b64 (1 baris base64)
echo.

REM Tampilkan preview
powershell -Command "Get-Content '%TEMP%\yt_cookies.b64' | Select-Object -First 1 | ForEach-Object { Write-Host ('Base64 length: ' + $_.Length + ' chars') ; Write-Host ('First 80: ' + $_.Substring(0,[Math]::Min(80,$_.Length)) + '...') }"

pause
