@echo off
chcp 65001 >nul
setlocal
rem === Satu file untuk PASANG pertama kali DAN PERBARUI. ===
rem Taruh file ini di folder aplikasi, lalu klik dua kali.
rem pengaturan.json, progres, dan log TIDAK disentuh.
set REPO=semogaberdampak/otomasi
set EXE=AutomasiNota.exe
set URL=https://github.com/%REPO%/releases/latest/download/%EXE%

cd /d "%~dp0"
taskkill /F /IM %EXE% >nul 2>&1
echo Mengunduh versi terbaru...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%URL%' -OutFile '%EXE%.baru' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
  echo GAGAL mengunduh. Periksa koneksi internet lalu coba lagi.
  del "%EXE%.baru" >nul 2>&1
  pause
  exit /b 1
)
move /Y "%EXE%.baru" "%EXE%" >nul
echo Selesai. Menjalankan aplikasi...
start "" "%EXE%"
