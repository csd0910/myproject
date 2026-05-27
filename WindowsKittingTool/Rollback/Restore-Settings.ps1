# Restore Settings (Rollback Script)

# 設定とログの読み込み
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
. (Join-Path $PSScriptRoot "..\Config.ps1")
. (Join-Path $PSScriptRoot "..\Lib\Logger.ps1")

Write-KittingLog "設定の復元（ロールバック）を開始します..."

# 1. UACの有効化
Invoke-WithRetry {
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 1
} -TaskName "UAC有効化"

# 2. おすすめ表示の復活
Invoke-WithRetry {
    $Path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
    Set-ItemProperty -Path $Path -Name "SystemPaneSuggestionsEnabled" -Value 1
} -TaskName "おすすめ表示有効化"

# 3. サービスの再開
$Services = @("SharedAccess", "WSearch")
foreach ($svc in $Services) {
    Set-Service -Name $svc -StartupType Automatic
    Start-Service -Name $svc -ErrorAction SilentlyContinue
}

Write-KittingLog "復元が完了しました。変更を反映させるには再起動してください。" -Level Success
