@echo off
cd /d %~dp0

:: --- 1. OS・環境設定スクリプトの実行 ---
:: 先ほど作成したユーザー作成・電源設定などのPowerShellを実行
powershell.exe -ExecutionPolicy Bypass -File setup.ps1

:: --- 2. Google Chrome (MSI版) のインストール ---
:: /qn: 画面を出さない, /norestart: 勝手に再起動しない
start /wait msiexec /i "googlechromestandaloneenterprise64.msi" /qn /norestart

:: --- 3. Adobe Acrobat Reader (オフライン版) のインストール ---
:: /sAll: サイレント, /rs: 再起動抑制, EULA_ACCEPT: 利用規約自動同意
start /wait AcroRdrDC2600121431_ja_JP.exe /sAll /rs /msi EULA_ACCEPT=YES

:: --- 4. Microsoft 365 のインストール ---
:: 伊藤さんの指定したXMLを使用して構成
start /wait setup.exe /configure configuration-MS365-x64.xml

exit /b