@echo off
REM SKYSEA用 サイレントセキュアブート証明書問題調査ツール
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "Check-SecureBootCert.ps1"
