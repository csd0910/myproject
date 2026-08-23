@echo off
title 7-Zip 超シンプルインストーラー
echo 7-Zip 超シンプルインストーラー
echo ====================================

REM 管理者権限確認
echo 管理者権限の確認中...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 管理者権限がありません。
    echo 右クリックして「管理者として実行」してください。
    pause
    exit /b 1
)
echo 管理者権限：OK

REM 競合ソフトのアンインストール（最小限）
echo.
echo 競合ソフトのチェック中...
set "found=0"

REM 最小限のチェック（WinRARのみ例として）
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "WinRAR" > nul 2>&1
if %errorlevel% equ 0 (
    echo WinRAR が見つかりました。アンインストールします。
    set "found=1"
    
    for /f "tokens=*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "WinRAR" 2^>nul') do (
        for /f "tokens=2*" %%b in ('reg query "%%a" /v "UninstallString" 2^>nul') do (
            if not "%%c"=="" (
                echo アンインストールコマンド: %%c
                start /wait %%c /S
                echo WinRAR のアンインストールを試みました。
            )
        )
    )
)

REM Lhaplusのチェック
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Lhaplus" > nul 2>&1
if %errorlevel% equ 0 (
    echo Lhaplus が見つかりました。アンインストールします。
    set "found=1"
    
    for /f "tokens=*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Lhaplus" 2^>nul') do (
        for /f "tokens=2*" %%b in ('reg query "%%a" /v "UninstallString" 2^>nul') do (
            if not "%%c"=="" (
                echo アンインストールコマンド: %%c
                start /wait %%c /S
                echo Lhaplus のアンインストールを試みました。
            )
        )
    )
)

if "%found%"=="0" (
    echo 競合するアーカイブソフトは見つかりませんでした。
)

REM 7-Zipのダウンロードとインストール
echo.
echo 7-Zipのインストール準備中...

REM システムアーキテクチャの検出
if exist "%ProgramFiles(x86)%" (
    echo 64ビットシステムを検出しました
    set "download_url=https://www.7-zip.org/a/7z2501-x64.msi"
) else (
    echo 32ビットシステムを検出しました
    set "download_url=https://www.7-zip.org/a/7z2501.msi"
)

REM インストーラーのダウンロード
echo インストーラーをダウンロードしています...
echo URL: %download_url%

if exist "%TEMP%\7z-install.msi" del "%TEMP%\7z-install.msi"

powershell -Command "(New-Object System.Net.WebClient).DownloadFile('%download_url%', '%TEMP%\7z-install.msi')"

if not exist "%TEMP%\7z-install.msi" (
    echo ダウンロードに失敗しました。
    echo ブラウザでダウンロードページを開きます。
    start https://www.7-zip.org/download.html
    pause
    exit /b 1
)

REM インストール実行
echo.
echo 7-Zipをインストールしています...
start /wait msiexec /i "%TEMP%\7z-install.msi" /qn

echo インストール処理中...
timeout /t 10 > nul

REM インストール確認
set "install_ok=0"
if exist "%ProgramFiles%\7-Zip\7zG.exe" (
    set "sevenzip_path=%ProgramFiles%\7-Zip\7zG.exe"
    set "install_ok=1"
)

if exist "%ProgramFiles(x86)%\7-Zip\7zG.exe" (
    set "sevenzip_path=%ProgramFiles(x86)%\7-Zip\7zG.exe"
    set "install_ok=1"
)

if "%install_ok%"=="1" (
    echo 7-Zipのインストールに成功しました！
    
    REM 解凍設定
    echo 設定を適用しています...
    reg add "HKCR\Applications\7zG.exe\shell\open\command" /ve /t REG_SZ /d "\"%sevenzip_path%\" x \"%%1\" -o*" /f
    
    echo.
    echo ====================================
    echo  7-Zipのインストールが完了しました！
    echo  ダブルクリックで解凍する設定が適用されました
    echo ====================================
) else (
    echo 自動インストールに失敗しました。
    echo インストーラーを手動で実行します...
    start "" "%TEMP%\7z-install.msi"
    echo インストールが完了したら何かキーを押してください...
    pause > nul
)

REM 終了
echo.
echo 処理を終了します。何かキーを押してください...
pause > nul