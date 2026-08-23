$path = '.\Set-CorporateStandardEnvironment.ps1'
$lines = Get-Content $path
$startIndex = -1
$endIndex = -1

for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match '^# Network Settings') {
        $startIndex = $i
    }
    if ($startIndex -ge 0 -and $lines[$i] -match '^# =========================================') {
        $endIndex = $i - 1
        break
    }
}

if ($startIndex -ge 0 -and $endIndex -gt $startIndex) {
    Write-Host "Found block: $startIndex to $endIndex"
    $newLines = @()
    if ($startIndex -gt 0) {
        $newLines += $lines[0..($startIndex-1)]
    }

    # Add Network block
    $newLines += "# --- Network Configuration ---"
    $newLines += 'Write-Host "`n[ネットワーク設定の適用]" -ForegroundColor Cyan'
    $newLines += 'if ($setStaticIP -match "^y" -and -not [string]::IsNullOrWhiteSpace($ipAddress)) {'
    $newLines += '    Write-Host "有線LANの固定IPを設定しています..."'
    $newLines += '    $adapter = Get-NetAdapter | Where-Object { $_.Status -eq "Up" -and $_.MediaType -eq "802.3" } | Select-Object -First 1'
    $newLines += '    if (-not $adapter) {'
    $newLines += '        $adapter = Get-NetAdapter -InterfaceDescription "*Ethernet*", "*GbE*" | Select-Object -First 1'
    $newLines += '    }'
    $newLines += '    if ($adapter) {'
    $newLines += '        $prefix = 24'
    $newLines += '        if ($subnetMask -eq "255.255.0.0") { $prefix = 16 }'
    $newLines += '        New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $ipAddress -PrefixLength $prefix -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null'
    $newLines += '        Set-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $ipAddress -PrefixLength $prefix -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null'
    $newLines += '        if (-not [string]::IsNullOrWhiteSpace($dns1)) {'
    $newLines += '            $dnsServers = @($dns1)'
    $newLines += '            if (-not [string]::IsNullOrWhiteSpace($dns2)) { $dnsServers += $dns2 }'
    $newLines += '            Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ServerAddresses $dnsServers -ErrorAction SilentlyContinue | Out-Null'
    $newLines += '        }'
    $newLines += '        Add-Check "有線固定IP設定 ($ipAddress)" "OK"'
    $newLines += '    } else {'
    $newLines += '        Add-Check "有線固定IP設定" "NG (Adapter not found)"'
    $newLines += '    }'
    $newLines += '}'
    $newLines += ''
    $newLines += '# 2. Wi-Fi Configuration'
    $newLines += 'if ($setWifi -match "^y" -and -not [string]::IsNullOrWhiteSpace($wifiSSID)) {'
    $newLines += '    Write-Host "Wi-Fiプロファイルを構成しています..."'
    $newLines += '    $xml = "<?xml version=`"1.0`"?><WLANProfile xmlns=`"http://www.microsoft.com/networking/WLAN/profile/v1`"><name>$wifiSSID</name><SSIDConfig><SSID><name>$wifiSSID</name></SSID></SSIDConfig><connectionType>ESS</connectionType><connectionMode>auto</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>$wifiPass</keyMaterial></sharedKey></security></MSM></WLANProfile>"'
    $newLines += '    $xmlPath = "$env:TEMP\wifi_profile.xml"'
    $newLines += '    $xml | Out-File -FilePath $xmlPath -Encoding UTF8'
    $newLines += '    netsh wlan add profile filename=`"$xmlPath`" | Out-Null'
    $newLines += '    netsh wlan connect name=`"$wifiSSID`" | Out-Null'
    $newLines += '    Remove-Item $xmlPath -ErrorAction SilentlyContinue'
    $newLines += '    Add-Check "Wi-Fi設定 ($wifiSSID)" "OK"'
    $newLines += '}'
    $newLines += ''
    $newLines += '# 3. NAS (Network Drive) Mapping'
    $newLines += 'Write-Host "社内NAS(Y:)ドライブをマウントしています..."'
    $newLines += '$nasPath = "\\frt-nas\01_全社共有"'
    $newLines += '$nasPathFallback = "\\10.85.33.230\01_全社共有"'
    $newLines += '$user = "frt_user"'
    $newLines += '$pass = "Forest0720@"'
    $newLines += 'if (Get-PSDrive Y -ErrorAction SilentlyContinue) {'
    $newLines += '    Remove-SmbMapping -LocalPath "Y:" -Force -UpdateProfile -ErrorAction SilentlyContinue'
    $newLines += '    cmd.exe /c "net use Y: /delete /y 2>NUL"'
    $newLines += '}'
    $newLines += 'Start-Sleep -Seconds 3'
    $newLines += 'cmd.exe /c "net use Y: `"$nasPath`" /user:$user `"$pass`" /persistent:yes 2>NUL"'
    $newLines += 'if ($LASTEXITCODE -ne 0) {'
    $newLines += '    Write-Host "\\frt-nas への接続に失敗しました。IPアドレスで再試行します..." -ForegroundColor Yellow'
    $newLines += '    cmd.exe /c "net use Y: `"$nasPathFallback`" /user:$user `"$pass`" /persistent:yes 2>NUL"'
    $newLines += '}'
    $newLines += 'if (Test-Path "Y:\") {'
    $newLines += '    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##frt-nas#01_全社共有"'
    $newLines += '    if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }'
    $newLines += '    Set-ItemProperty -Path $regPath -Name "_LabelFromReg" -Value "01_全社共有 (\\frt-nas)" -Force'
    $newLines += '    $regPathFallback = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##10.85.33.230#01_全社共有"'
    $newLines += '    if (-not (Test-Path $regPathFallback)) { New-Item -Path $regPathFallback -Force | Out-Null }'
    $newLines += '    Set-ItemProperty -Path $regPathFallback -Name "_LabelFromReg" -Value "01_全社共有 (\\frt-nas)" -Force'
    $newLines += '    Add-Check "NAS接続設定 (Y:)" "OK"'
    $newLines += '} else {'
    $newLines += '    Add-Check "NAS接続設定 (Y:)" "NG (未到達)"'
    $newLines += '}'
    $newLines += ''

    $newLines += $lines[($endIndex + 1)..($lines.Length-1)]
    $newLines | Out-File $path -Encoding UTF8
    Write-Host "Success"
} else {
    Write-Host "Could not find target block bounds. startIndex: $startIndex, endIndex: $endIndex"
}
