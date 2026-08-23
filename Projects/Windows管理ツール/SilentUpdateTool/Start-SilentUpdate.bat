@echo off
REM SKYSEA等からシステム権限/管理者権限で実行される想定
REM 画面を一切出さずにPowerShellをバックグラウンド実行します

cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "Run-SilentUpdate.ps1"
