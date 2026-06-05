@echo off
chcp 65001 >nul
echo =========================================
echo アプリ更新チェックのセットアップ（テスト用）
echo =========================================

:: 管理者権限チェック
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo 【エラー】管理者権限がありません。右クリックから「管理者として実行」してください。
    pause
    exit /b
)

set TARGET_DIR=C:\AppUpdaterTest

echo.
echo 1. テスト用フォルダ %TARGET_DIR% を作成し、ファイルを配置しています...
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
)

copy /Y "%~dp0AppUpdateCheck.ps1" "%TARGET_DIR%\AppUpdateCheck.ps1"
copy /Y "%~dp0nas_logger.py" "%TARGET_DIR%\nas_logger.py"

echo.
echo 2. タスクスケジューラに登録しています...
:: 古いテスト用タスクを削除（念のため）
schtasks /delete /tn "AppUpdateCheckTest" /f >nul 2>&1
:: タスク名を変更して登録 (/f で上書きするため常に1つです)
schtasks /create /tn "AppUpdater(システム運営課)" /tr "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File %TARGET_DIR%\AppUpdateCheck.ps1" /sc onlogon /rl highest /f
if %errorlevel% neq 0 (
    echo 【エラー】登録に失敗しました。
    pause
    exit /b
)

echo.
echo テスト用のセットアップが完了しました！
echo （タスク「AppUpdater(システム運営課)」として登録されました）
echo.
echo テストとして今すぐ実行する場合は、コマンドプロンプトで schtasks /run /tn "AppUpdater(システム運営課)" を実行してください。
pause
