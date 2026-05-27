function Write-KittingLog {
    param ([Parameter(Mandatory=$true)][string]$Message, [ValidateSet("Info", "Success", "Warning", "Error")][string]$Level = "Info")
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$TimeStamp] [$Level] $Message"
    
    # 画面出力
    $Color = switch($Level) { "Success" { "Green" } "Warning" { "Yellow" } "Error" { "Red" } default { "White" } }
    Write-Host $LogMessage -ForegroundColor $Color
    
    # ファイル出力 (修正ポイント: $LogMessage を書き込む)
    try {
        if ($script:KittingConfig.LogPath) {
            $LogMessage | Out-File -FilePath $script:KittingConfig.LogPath -Append -Encoding UTF8 -ErrorAction SilentlyContinue
        }
    } catch {}
}

function Invoke-WithRetry {
    param ([Parameter(Mandatory=$true)][scriptblock]$ScriptBlock, [int]$MaxRetries = 3, [string]$TaskName = "処理")
    $RetryCount = 0; $Success = $false
    while (-not $Success -and $RetryCount -lt $MaxRetries) {
        try { & $ScriptBlock; $Success = $true; Write-KittingLog "$TaskName が成功しました。" -Level Success }
        catch { 
            $RetryCount++; 
            Write-KittingLog "$TaskName に失敗 ($RetryCount/$MaxRetries): $($_.Exception.Message)" -Level Warning; 
            Start-Sleep -Seconds 2 
        }
    }
    if (-not $Success) { Write-KittingLog "$TaskName は中断されました。" -Level Error; return $false }
    return $true
}
