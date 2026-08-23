@echo off
:: Batch file to run Kitting PowerShell script bypassing execution policy
cd /d "%~dp0"

echo =========================================
echo Starting OA Terminal Kitting Tool (Ver.1)
echo =========================================

powershell -ExecutionPolicy Bypass -NoProfile -File "Set-CorporateStandardEnvironment_v1.ps1"

echo.
echo =========================================
echo Kitting process finished.
echo =========================================
pause
