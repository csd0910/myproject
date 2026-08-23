@echo off
:: Batch file to run App Installation Kitting script
cd /d "%~dp0"

echo =========================================
echo Starting OA Terminal Kitting Tool (Ver.2: Apps)
echo =========================================

powershell -ExecutionPolicy Bypass -NoProfile -File "Install-Applications.ps1"

echo.
echo =========================================
echo App Installation process finished.
echo =========================================
pause
