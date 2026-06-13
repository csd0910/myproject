@echo off
REM SKYSEA用 サイレント資格情報問題調査ツール

cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "Check-CredentialIssue.ps1"
