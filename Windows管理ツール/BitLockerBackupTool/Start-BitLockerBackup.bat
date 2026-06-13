@echo off
REM SKYSEA用 サイレントBitLocker回復キーバックアップツール
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "Backup-BitLockerKey.ps1"
