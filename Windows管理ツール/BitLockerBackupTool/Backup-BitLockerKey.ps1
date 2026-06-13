$ErrorActionPreference = "Stop"
$ComputerName = $env:COMPUTERNAME
$Drive = "C:"

# NASアクセス情報
$NasIP = "10.85.33.230"
$NasUser = "frt_user"
$NasPass = "Forest0720@"

# ログ保存先ディレクトリ
$LogDir = "\\$NasIP\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\BitLocker回復キー管理"
$CsvPath = "$LogDir\BitLocker_RecoveryKeys.csv"

function Write-NasKey {
    param([string]$Key)
    $Timestamp = Get-Date -Format "yyyy/MM/dd HH:mm:ss"
    
    try {
        if (-not (Test-Path $LogDir)) {
            New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
        }
        # ファイルがない場合はヘッダーを作成
        if (-not (Test-Path $CsvPath)) {
            '"取得日時","PC名","回復キー"' | Out-File -FilePath $CsvPath -Encoding UTF8 -Force
        }
        
        $CsvLine = "`"$Timestamp`",`"$ComputerName`",`"$Key`""
        $CsvLine | Out-File -FilePath $CsvPath -Append -Encoding UTF8
    } catch {
        # 失敗時はローカル退避
        $LocalCsv = "C:\Windows\Temp\BitLockerKey_$ComputerName.csv"
        "`"$Timestamp`",`"$ComputerName`",`"$Key`"" | Out-File -FilePath $LocalCsv -Append -Encoding UTF8
    }
}

try {
    # NAS資格情報登録
    cmdkey /add:$NasIP /user:$NasUser /pass:$NasPass | Out-Null

    # CドライブのBitLocker情報を取得
    $Volume = Get-BitLockerVolume -MountPoint $Drive -ErrorAction SilentlyContinue

    if (-not $Volume) {
        Write-NasKey "BitLocker非対応 または Cドライブ取得失敗"
        exit
    }

    # 回復パスワード(48桁の数字)のプロテクターが存在するか確認
    $RecoveryKey = $Volume.KeyProtector | Where-Object { $_.KeyProtectorType -eq 'RecoveryPassword' }
    
    # まだ作られていない場合は、強制的に生成(追加)する
    if (-not $RecoveryKey) {
        Add-BitLockerKeyProtector -MountPoint $Drive -RecoveryPasswordProtector -ErrorAction SilentlyContinue | Out-Null
        
        # 追加後に再取得
        $Volume = Get-BitLockerVolume -MountPoint $Drive
        $RecoveryKey = $Volume.KeyProtector | Where-Object { $_.KeyProtectorType -eq 'RecoveryPassword' }
    }

    if ($RecoveryKey) {
        # 複数のキーがある場合(通常は1つ)はスラッシュ区切りで結合
        $KeyString = ($RecoveryKey | Select-Object -ExpandProperty RecoveryPassword) -join " / "
        
        # 回復キーをNASへ保存！
        Write-NasKey $KeyString
        
        # ※ もし中途半端な状態（デバイスの暗号化待機中など）であれば、ここで暗号化を「確定」させる
        if ($Volume.VolumeStatus -eq 'Decrypted' -or $Volume.ProtectionStatus -eq 'Off') {
            Enable-BitLocker -MountPoint $Drive -EncryptionMethod XtsAes128 -UsedSpaceOnly -SkipHardwareTest -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
        }
    } else {
        Write-NasKey "回復キーの生成に失敗しました（TPM未搭載やエラー）"
    }

} catch {
    Write-NasKey "エラー発生: $($_.Exception.Message)"
}
