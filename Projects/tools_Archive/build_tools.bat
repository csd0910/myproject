@echo off
chcp 65001 > NUL
echo =========================================
echo サイボウズメールエクスポート ビルドツール
echo =========================================
echo.

cd /d "%~dp0"

echo [1/3] 仮想環境を有効化しています...
call ..\.venv\Scripts\activate.bat

echo [2/3] MBox変換ツールをビルドしています... (既存の設定を流用)
pyinstaller --noconfirm --onefile --noconsole cybozu_mbox_converter.py

echo [3/3] メールエクスポートツールをビルドしています... (Selenium連携込み)
pyinstaller --noconfirm --onefile --noconsole --collect-all selenium cybozu_email_exporter.py

echo.
echo =========================================
echo ビルドが完了しました！！
echo 「tools\dist」フォルダ内を確認してください。
echo =========================================
pause
