# UIテスト用スクリプト
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $PSScriptRoot

# UI関数の読み込み
. ".\Lib\Utils.ps1"

# フォームの表示
Write-Host "UIを起動しています..." -ForegroundColor Cyan
$Result = Get-KittingInput

if ($Result) {
    Write-Host "--- 入力された内容 ---" -ForegroundColor Green
    $Result | Out-String | Write-Host
} else {
    Write-Host "キャンセルされました。" -ForegroundColor Yellow
}

Write-Host "確認が終わったらこの画面を閉じてください。"
pause
