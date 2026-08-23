$path = 'C:\Users\フォーレスト026\MyProject\tools\PC_Kitting\Set-CorporateStandardEnvironment.ps1'
$content = Get-Content $path -Raw

$pattern = '(?s)# Network Settings\r\nif \(\$setStaticIP.*?(?=# =========================================\r\n# 3\. Apply System Policies)'

$newNetworkBlock = @"
# --- Network Configuration ---
Write-Host "`n[ネットワーク設定の適用]" -ForegroundColor Cyan

# 1. Wired IP Configuration
if (`$setStaticIP -match "^y" -and -not [string]::IsNullOrWhiteSpace(`$ipAddress)) {
    Write-Host "有線LANの固定IPを設定しています..."
    `$adapter = Get-NetAdapter | Where-Object { `$_.Status -eq "Up" -and `$_.MediaType -eq "802.3" } | Select-Object -First 1
    if (-not `$adapter) {
        `$adapter = Get-NetAdapter -InterfaceDescription "*Ethernet*", "*GbE*" | Select-Object -First 1
    }
    if (`$adapter) {
        `$prefix = 24
        if (`$subnetMask -eq "255.255.0.0") { `$prefix = 16 }
        New-NetIPAddress -InterfaceIndex `$adapter.ifIndex -IPAddress `$ipAddress -PrefixLength `$prefix -DefaultGateway `$gateway -ErrorAction SilentlyContinue | Out-Null
        Set-NetIPAddress -InterfaceIndex `$adapter.ifIndex -IPAddress `$ipAddress -PrefixLength `$prefix -DefaultGateway `$gateway -ErrorAction SilentlyContinue | Out-Null
        if (-not [string]::IsNullOrWhiteSpace(`$dns1)) {
            `$dnsServers = @(`$dns1)
            if (-not [string]::IsNullOrWhiteSpace(`$dns2)) { `$dnsServers += `$dns2 }
            Set-DnsClientServerAddress -InterfaceIndex `$adapter.ifIndex -ServerAddresses `$dnsServers -ErrorAction SilentlyContinue | Out-Null
        }
        Add-Check "有線固定IP設定 (`$ipAddress)" "OK"
    } else {
        Add-Check "有線固定IP設定" "NG (Adapter not found)"
    }
}

# 2. Wi-Fi Configuration
if (`$setWifi -match "^y" -and -not [string]::IsNullOrWhiteSpace(`$wifiSSID)) {
    Write-Host "Wi-Fiプロファイルを構成しています..."
    `$xml = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>`$wifiSSID</name>
    <SSIDConfig>
        <SSID>
            <name>`$wifiSSID</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>`$wifiPass</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"@
    `$xmlPath = "`$env:TEMP\wifi_profile.xml"
    `$xml | Out-File -FilePath `$xmlPath -Encoding UTF8
    netsh wlan add profile filename="`$xmlPath" | Out-Null
    netsh wlan connect name="`$wifiSSID" | Out-Null
    Remove-Item `$xmlPath -ErrorAction SilentlyContinue
    Add-Check "Wi-Fi設定 (`$wifiSSID)" "OK"
}

# 3. NAS (Network Drive) Mapping
Write-Host "社内NAS(Y:)ドライブをマウントしています..."
`$nasPath = "\\frt-nas\01_全社共有"
`$nasPathFallback = "\\10.85.33.230\01_全社共有"
`$user = "frt_user"
`$pass = "Forest0720@"

if (Get-PSDrive Y -ErrorAction SilentlyContinue) {
    Remove-SmbMapping -LocalPath "Y:" -Force -UpdateProfile -ErrorAction SilentlyContinue
    cmd.exe /c "net use Y: /delete /y 2>NUL"
}
Start-Sleep -Seconds 3

cmd.exe /c "net use Y: `"`$nasPath`" /user:`$user `"`$pass`" /persistent:yes 2>NUL"
if (`$LASTEXITCODE -ne 0) {
    Write-Host "\\frt-nas への接続に失敗しました。IPアドレスで再試行します..." -ForegroundColor Yellow
    cmd.exe /c "net use Y: `"`$nasPathFallback`" /user:`$user `"`$pass`" /persistent:yes 2>NUL"
}

if (Test-Path "Y:\") {
    # Set Label in Registry
    `$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##frt-nas#01_全社共有"
    if (-not (Test-Path `$regPath)) { New-Item -Path `$regPath -Force | Out-Null }
    Set-ItemProperty -Path `$regPath -Name "_LabelFromReg" -Value "01_全社共有 (\\frt-nas)" -Force
    
    `$regPathFallback = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##10.85.33.230#01_全社共有"
    if (-not (Test-Path `$regPathFallback)) { New-Item -Path `$regPathFallback -Force | Out-Null }
    Set-ItemProperty -Path `$regPathFallback -Name "_LabelFromReg" -Value "01_全社共有 (\\frt-nas)" -Force

    Add-Check "NAS接続設定 (Y:)" "OK"
} else {
    Add-Check "NAS接続設定 (Y:)" "NG (未到達)"
}

"@

$content = $content -replace $pattern, $newNetworkBlock
$content | Out-File $path -Encoding UTF8
