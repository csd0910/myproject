@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "Start-Kitting.ps1"
pause
