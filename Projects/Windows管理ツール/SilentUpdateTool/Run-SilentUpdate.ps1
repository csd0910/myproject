$ErrorActionPreference = "Stop"
$ComputerName = $env:COMPUTERNAME

# NASアクセス情報 (環境に合わせて変更)
$NasIP = "10.85.33.230"
$NasUser = "frt_user"
$NasPass = "Forest0720@"

$LogDir = "\\$NasIP\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\WindowsUpdateログ"
$LogPath = "$LogDir\UpdateLog_$(Get-Date -Format 'yyyyMM').csv"

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
        # ログ書き込み失敗時はローカルに退避
        $LocalLog = "C:\Windows\Temp\UpdateLog_$ComputerName.csv"
        $LogLine | Out-File -FilePath $LocalLog -Append -Encoding UTF8
    }
}

try {
    # 1. NASへの資格情報登録
    cmdkey /add:$NasIP /user:$NasUser /pass:$NasPass | Out-Null
    Write-NasLog "開始" "Windows Update処理を開始しました。"

    # 2. PSWindowsUpdateモジュールの準備
    if (-not (Get-PackageProvider -Name NuGet -ErrorAction SilentlyContinue)) {
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Confirm:$false | Out-Null
    }
    if (-not (Get-Module -ListAvailable PSWindowsUpdate)) {
        Install-Module -Name PSWindowsUpdate -Force -SkipPublisherCheck -Confirm:$false -Scope AllUsers | Out-Null
    }
    Import-Module PSWindowsUpdate -Force

    # 3. Microsoft Update (Office, ドライバ等) の有効化
    Add-WUServiceManager -ServiceID "79662437-142b-4d4e-9d7c-9039175be469" -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

    # 4. 更新の実行 (画面を出さずにすべて適用)
    Write-NasLog "進行中" "更新プログラムのダウンロードとインストールを実行しています..."
    
    # ドライバ、Microsoft製品を含む全てのアップデートをインストール
    $UpdateResult = Get-WindowsUpdate -Install -AcceptAll -IgnoreReboot -MicrosoftUpdate

    # 5. 結果の判定とログ記録
    if ($UpdateResult) {
        $InstalledTitles = ($UpdateResult | Select-Object -ExpandProperty Title) -join "; "
        Write-NasLog "成功" "以下の更新が適用されました: $InstalledTitles"
    } else {
        Write-NasLog "成功(更新なし)" "適用可能な新しい更新プログラムはありませんでした。"
    }

    # 6. 再起動のスケジューリング (1分後に再起動)
    Write-NasLog "完了" "処理が完了しました。システムを再起動します。"
    shutdown /r /t 60 /c "Windows Updateが完了しました。再起動します。" /f

} catch {
    $ErrorMessage = $_.Exception.Message
    Write-NasLog "失敗" "エラーが発生しました: $ErrorMessage"
}
