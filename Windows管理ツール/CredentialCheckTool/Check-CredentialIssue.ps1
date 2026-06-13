$ErrorActionPreference = "Stop"
$ComputerName = $env:COMPUTERNAME

# NASアクセス情報
$NasIP = "10.85.33.230"
$NasUser = "frt_user"
$NasPass = "Forest0720@"

# ログ保存先ディレクトリ
$LogDir = "\\$NasIP\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\資格情報問題調査ログ"
$LogPath = "$LogDir\CredentialCheck_$(Get-Date -Format 'yyyyMMdd').csv"

function Write-NasLog {
    param([string]$Status, [string]$Details)
    $Timestamp = Get-Date -Format "yyyy/MM/dd HH:mm:ss"
    $LogLine = "`"$Timestamp`",`"$ComputerName`",`"$Status`",`"$($Details -replace "`"", "`'`")`""
    
    try {
        if (-not (Test-Path $LogDir)) {
            New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
        }
        $LogLine | Out-File -FilePath $LogPath -Append -Encoding UTF8
    } catch {
        $LocalLog = "C:\Windows\Temp\CredentialCheck_$ComputerName.csv"
        $LogLine | Out-File -FilePath $LocalLog -Append -Encoding UTF8
    }
}

try {
    # NAS資格情報登録
    cmdkey /add:$NasIP /user:$NasUser /pass:$NasPass | Out-Null

    # 【調査ロジック】
    $IssueDetected = $false
    $Details = ""

    # 例1: 過去30日間の DPAPI エラー (資格情報マネージャー破壊の原因) を検索
    $Events = Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-DPAPI'; Level=2; StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue
    if ($Events) {
        $IssueDetected = $true
        $Details += "DPAPIエラーが $($Events.Count) 件発生しています。"
    }

    # 例2: 資格情報マネージャーのサービス状態チェック
    $VaultService = Get-Service -Name "VaultSvc" -ErrorAction SilentlyContinue
    if ($VaultService -and $VaultService.Status -ne "Running") {
        $IssueDetected = $true
        $Details += " 資格情報マネージャーサービス(VaultSvc)が停止しています。"
    }

    # 結果をNASに送信
    if ($IssueDetected) {
        Write-NasLog "異常あり" "資格情報問題の兆候: $Details"
    } else {
        Write-NasLog "正常" "資格情報問題の兆候は見つかりませんでした。"
    }

} catch {
    Write-NasLog "エラー" "調査中にエラーが発生しました: $($_.Exception.Message)"
}
