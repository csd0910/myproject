function Get-PrefixLength([string]$mask) {
    try {
        $octets = $mask.Split('.')
        $bin = ""
        foreach ($o in $octets) { $bin += [Convert]::ToString([int]$o, 2).PadLeft(8, '0') }
        return ($bin.Replace('0', '').Length)
    } catch { return 24 }
}

function Set-NetworkStorage {
    param($InputData)
    Write-KittingLog "ネットワーク・ストレージ設定を開始します..."

    if ($InputData.StaticIP) {
        Invoke-WithRetry {
            $Adapter = Get-NetAdapter | Where-Object { $_.Status -eq "Up" } | Select-Object -First 1
            if ($Adapter) {
                $Prefix = Get-PrefixLength $InputData.SubnetMask
                
                # 既存のIPとデフォルトゲートウェイを完全に削除
                $Adapter | Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false
                Get-NetRoute -NextHop $InputData.Gateway -ErrorAction SilentlyContinue | Remove-NetRoute -Confirm:$false

                # 新規設定
                New-NetIPAddress -InterfaceAlias $Adapter.Name -IPAddress $InputData.IPAddress -PrefixLength $Prefix -DefaultGateway $InputData.Gateway -ErrorAction Stop
                Set-DnsClientServerAddress -InterfaceAlias $Adapter.Name -ServerAddresses ($InputData.DNS1, $InputData.DNS2) -ErrorAction Stop
            }
        } -TaskName "IP詳細設定"
    }

    $WlanAdapter = Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Wi-Fi|Wireless" }
    if ($WlanAdapter) {
        Invoke-WithRetry {
            $ssid = "FRTSYS-0001"; $password = "forest123456789"; $xmlPath = "$env:TEMP\wifi_profile.xml"
            $xml = "<?xml version=`"1.0`"?><WLANProfile xmlns=`"http://www.microsoft.com/networking/WLAN/profile/v1`"><name>$ssid</name><SSIDConfig><SSID><name>$ssid</name></SSIDConfig><connectionType>ESS</connectionType><connectionMode>auto</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>$password</keyMaterial></sharedKey></security></MSM></WLANProfile>"
            $xml | Out-File -FilePath $xmlPath -Encoding ASCII
            netsh wlan add profile filename=$xmlPath | Out-Null
            netsh wlan connect name=$ssid | Out-Null
            Start-Sleep -Seconds 5
        } -TaskName "Wi-Fi自動接続"
    }

    Invoke-WithRetry {
        cmdkey /add:10.85.33.230 /user:frt_user /pass:Forest0720@
        cmdkey /add:frt-nas /user:frt_user /pass:Forest0720@
    } -TaskName "NAS資格情報保存"

    Invoke-WithRetry {
        $DriveLetter = "Y:"; $Target = $script:KittingConfig.NASPath
        if (Test-Path $DriveLetter) {
            (New-Object -ComObject WScript.Network).RemoveNetworkDrive($DriveLetter, $true, $true)
        }
        New-PSDrive -Name "Y" -PSProvider FileSystem -Root $Target -Persist -ErrorAction Stop
    } -TaskName "Yドライブ割り当て"
}
