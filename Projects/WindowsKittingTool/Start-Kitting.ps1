$script:KittingRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $script:KittingRoot

. ".\Config.ps1"; . ".\Lib\Logger.ps1"; . ".\Lib\Utils.ps1"
. ".\Modules\01_BaseSettings.ps1"; . ".\Modules\02_NetworkStorage.ps1"; . ".\Modules\03_AppInstall.ps1"; . ".\Modules\04_Optimization.ps1"

$transcriptPath = Join-Path $script:KittingRoot "Console_Output.log"
Start-Transcript -Path $transcriptPath -Append -Force

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "管理者権限で実行してください。" -ForegroundColor Red; pause; Stop-Transcript; exit
}

Write-KittingLog "=== Windows キッティングツール 開始 ==="
$InputData = Get-KittingInput
if (-not $InputData) { Stop-Transcript; exit }

try {
    # 【爆速設定フェーズ】先に終わらせる
    Set-NetworkStorage -InputData $InputData
    Set-BaseSettings -InputData $InputData
    Set-Optimization
    
    # 【じっくりインストールフェーズ】
    Install-Applications
    Finalize-Kitting  # ここでWindowsUpdate
    
    Write-KittingLog "=== 全工程完了 ===" -Level Success
    Write-KittingLog "5秒後に自動再起動します..."
    for ($i = 5; $i -gt 0; $i--) { Write-Host "$i... " -NoNewline; Start-Sleep -Seconds 1 }
    Stop-Transcript
    Restart-Computer -Force
} catch {
    Write-KittingLog "重大なエラー: $($_.Exception.Message)" -Level Error
    Stop-Transcript; pause
}
