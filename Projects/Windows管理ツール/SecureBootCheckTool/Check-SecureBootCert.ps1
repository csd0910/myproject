$ErrorActionPreference = "Stop"
$ComputerName = $env:COMPUTERNAME

# NASアクセス情報
$NasIP = "10.85.33.230"
$NasUser = "frt_user"
$NasPass = "Forest0720@"

# ログ保存先ディレクトリ
$LogDir = "\\$NasIP\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\SecureBoot調査ログ"
$LogPath = "$LogDir\SecureBootCheck_$(Get-Date -Format 'yyyyMMdd').csv"

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
        $LocalLog = "C:\Windows\Temp\SecureBootCheck_$ComputerName.csv"
        $LogLine | Out-File -FilePath $LocalLog -Append -Encoding UTF8
    }
}

try {
    # NAS資格情報登録
    cmdkey /add:$NasIP /user:$NasUser /pass:$NasPass | Out-Null

    # SecureBootが有効か確認
    $secureBootEnabled = $false
    try {
        $secureBootEnabled = Confirm-SecureBootUEFI
    } catch {
        Write-NasLog "対象外" "この端末はセキュアブート機能に非対応です。"
        exit
    }

    if (-not $secureBootEnabled) {
        Write-NasLog "対象外" "この端末はセキュアブートが無効になっています。"
        exit
    }

    $IssueDetected = $false
    $Details = ""

    # UEFI DBの確認
    try {
        $db = Get-SecureBootUEFI -Name db
        $dbString = [System.Text.Encoding]::ASCII.GetString($db.bytes)
        
        if ($dbString -match "Windows UEFI CA 2023") {
            $Details += "DB: 新証明書(2023)あり。 "
        } else {
            $IssueDetected = $true
            $Details += "DB: 新証明書(2023)なし（将来の起動不能リスクあり）。 "
        }
    } catch {
        $IssueDetected = $true
        $Details += "DB: 読み取りエラー。 "
    }
    
    # 結果をNASに送信
    if ($IssueDetected) {
        Write-NasLog "要対応(危険)" "脆弱性リスクあり: $Details"
    } else {
        Write-NasLog "正常(更新済)" "問題なし: $Details"
    }

} catch {
    Write-NasLog "エラー" "調査中にエラーが発生しました: $($_.Exception.Message)"
}
