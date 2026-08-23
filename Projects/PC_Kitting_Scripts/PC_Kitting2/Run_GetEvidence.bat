@echo off
:: Batch file to run PowerShell script bypassing execution policy
cd /d "%~dp0"

echo =========================================
echo Starting Evidence Collection Script...
echo =========================================

powershell -ExecutionPolicy Bypass -NoProfile -File "Get-PCRegistryEvidence.ps1"

echo.
echo =========================================
echo Script execution finished.
echo If you see red error messages above,
echo please take a screenshot or copy the error.
echo =========================================
pause
