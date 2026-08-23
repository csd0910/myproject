@echo off
cd /d "%~dp0"
echo 稟議ツールを起動しています...
..\..\.venv\Scripts\python.exe ringi_tool.py
if errorlevel 1 (
    echo エラーが発生しました。
    pause
)
