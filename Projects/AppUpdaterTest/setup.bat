@echo off
chcp 65001 >nul
echo アプリ更新チェックのセットアップ（システム運営課）
echo =========================================

:: 管理者権限チェック
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo 【エラー】管理者権限がありません。
    exit /b 1
)

set TARGET_DIR=C:\AppUpdaterTest

echo.
echo 1. テスト用フォルダ %TARGET_DIR% を作成し、ファイルを配置しています...
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
)

copy /Y "%~dp0AppUpdateCheck.ps1" "%TARGET_DIR%\AppUpdateCheck.ps1"
:: 完全サイレント実行用のVBSもコピー
copy /Y "%~dp0RunSilent.vbs" "%TARGET_DIR%\RunSilent.vbs"

echo.
echo 2. タスクスケジューラに登録しています...
:: 古いテスト用タスクを削除（念のため）
schtasks /delete /tn "AppUpdateCheckTest" /f >nul 2>&1
:: タスク名を変更して登録 (RunSilent.vbs を経由して完全非表示化)
schtasks /create /tn "AppUpdater(システム運営課)" /tr "wscript.exe \"%TARGET_DIR%\RunSilent.vbs\"" /sc onlogon /rl highest /f

if %errorlevel% neq 0 (
    echo 【エラー】登録に失敗しました。
    exit /b 1
)

echo.
echo セットアップが完了しました！
echo （タスク「AppUpdater(システム運営課)」として登録されました）