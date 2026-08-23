@echo off
:: Batch file to run Kitting script with Rollback support
cd /d "%~dp0"

echo =========================================
echo Starting OA Terminal Kitting Tool (Ver.1)
echo =========================================

powershell -ExecutionPolicy Bypass -NoProfile -File "Set-CorporateStandardEnvironment.ps1"

echo.
echo =========================================
echo Kitting process finished.
echo Check the Logs folder for Checklist and Rollback script.
echo =========================================
pause
