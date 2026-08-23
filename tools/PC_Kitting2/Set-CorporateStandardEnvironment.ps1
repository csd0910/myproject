<#
.SYNOPSIS
OA Terminal Kitting Tool (Ver.1: Full Settings & Rollback generation)
#>

# 1. Admin Check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "管理者権限がありません。管理者権限で再起動します..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = (Get-Item $PSCommandPath).DirectoryName }
$LogsDir = Join-Path $scriptDir "Logs"
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir | Out-Null }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " OA端末 自動キッティングツール [Ver.1 - 完全版]" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 2. Inputs
Write-Host "--- [初期情報入力] ---" -ForegroundColor Green
$currentPCName = $env:COMPUTERNAME
$newPCName = Read-Host "1. 新しいPC名を入力 (そのままEnterで [$currentPCName] を維持)"
if ([string]::IsNullOrWhiteSpace($newPCName)) { $newPCName = $currentPCName }

$targetUser = Read-Host "2. 作成するローカルユーザー名 (例: SysAdmin / 空白でスキップ)"
$targetPass = ""
if (-not [string]::IsNullOrWhiteSpace($targetUser)) {
    $targetPass = Read-Host "3. $targetUser のパスワード"
}

$setStaticIP = Read-Host "4. 固定IP/DNSを設定しますか？ (すでに設定済み・またはDHCPなら 'n') (y/n) [n]"
$ipAddress = ""; $subnetMask = ""; $gateway = ""; $dns1 = ""; $dns2 = ""
if ($setStaticIP -match "^y") {
    $ipAddress = Read-Host "   - IPアドレス"
    $subnetMask = Read-Host "   - サブネットマスク (空白で 255.255.255.0)"
    if ([string]::IsNullOrWhiteSpace($subnetMask)) { $subnetMask = "255.255.255.0" }
    $gateway = Read-Host "   - デフォルトゲートウェイ (空白でスキップ)"
    $dns1 = Read-Host "   - プライマリDNS (空白でスキップ)"
    $dns2 = Read-Host "   - セカンダリDNS (空白でスキップ)"
}

$setWifi = Read-Host "5. 社内Wi-Fi(無線LAN)の接続設定を行いますか？ (y/n) [n]"
$wifiSSID = ""; $wifiPass = ""
if ($setWifi -match "^y") {
    $wifiSSID = Read-Host "   - SSID (空白で FRT-SYS0001)"
    if ([string]::IsNullOrWhiteSpace($wifiSSID)) { $wifiSSID = "FRT-SYS0001" }
    $wifiPass = Read-Host "   - パスワード (空白で forest123456789)"
    if ([string]::IsNullOrWhiteSpace($wifiPass)) { $wifiPass = "forest123456789" }
}

Write-Host "`nキッティング処理を開始します..." -ForegroundColor Yellow

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ChecklistFile = Join-Path $LogsDir "Checklist_$timestamp.txt"
$checklist = @()

function Add-Check {
    param($item, $status)
    $checklist += "[$status] $item"
    Write-Host "[$status] $item"
}

# =========================================
# 3. Apply System Policies (HKLM & Global)
# =========================================

# UAC Disable
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 0 -Force
Add-Check "UAC Disabled" "OK"

# Remote Desktop
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0 -Force
Enable-NetFirewallRule -Group "RemoteDesktop" -ErrorAction SilentlyContinue | Out-Null
Add-Check "RDP Enabled" "OK"

# NTP Server (コンパネ表記にも反映)
$serversPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DateTime\Servers"
if (-not (Test-Path $serversPath)) { New-Item -Path $serversPath -Force | Out-Null }
Set-ItemProperty -Path $serversPath -Name "1" -Value "ntp.nict.jp" -Force
Set-ItemProperty -Path $serversPath -Name "(Default)" -Value "1" -Force
Start-Process "w32tm" -ArgumentList "/config /manualpeerlist:ntp.nict.jp /syncfromflags:manual /update" -Wait -NoNewWindow
Start-Process "net" -ArgumentList "stop w32time" -Wait -NoNewWindow
Start-Process "net" -ArgumentList "start w32time" -Wait -NoNewWindow
Add-Check "NTP Set to ntp.nict.jp" "OK"

# Services (WSearch, ICS)
Set-Service -Name "WSearch" -StartupType Disabled -ErrorAction SilentlyContinue
Stop-Service -Name "WSearch" -Force -ErrorAction SilentlyContinue
Set-Service -Name "SharedAccess" -StartupType Disabled -ErrorAction SilentlyContinue
Stop-Service -Name "SharedAccess" -Force -ErrorAction SilentlyContinue
Add-Check "WSearch and ICS Disabled" "OK"

# Power Settings (Hibernate OFF, Button=Shutdown, Sleep=Never, HDD=0)
Start-Process "powercfg.exe" -ArgumentList "/hibernate off" -Wait -NoNewWindow
# 電源ボタンを押したとき = シャットダウン (3)
Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 7648efa3-dd9c-4e3e-b566-50f929386280 3" -Wait -NoNewWindow
Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 7648efa3-dd9c-4e3e-b566-50f929386280 3" -Wait -NoNewWindow
# スリープボタンを押したとき = 何もしない (0)
Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 96996bc0-ad50-47ec-923b-6f41874abc4e 0" -Wait -NoNewWindow
Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 96996bc0-ad50-47ec-923b-6f41874abc4e 0" -Wait -NoNewWindow
# ハードディスクの電源を切る = 0分
Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 0012ee47-9041-4b5d-9b77-535fba8b1442 6738e2c4-e8a5-4a42-b16a-e040e769756e 0" -Wait -NoNewWindow
Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 0012ee47-9041-4b5d-9b77-535fba8b1442 6738e2c4-e8a5-4a42-b16a-e040e769756e 0" -Wait -NoNewWindow
# スリープする = 0分
Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 238c9fa8-0aad-41ed-83f4-97be242c8f20 29f6c1db-86da-48c5-9f15-2320c0adfc4b 0" -Wait -NoNewWindow
Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 238c9fa8-0aad-41ed-83f4-97be242c8f20 29f6c1db-86da-48c5-9f15-2320c0adfc4b 0" -Wait -NoNewWindow
# 画面の電源を切る = 0分 (任意ですがスリープと合わせる)
Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 7516b95f-f776-4464-8c53-06167f40cc99 3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e 0" -Wait -NoNewWindow
Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 7516b95f-f776-4464-8c53-06167f40cc99 3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e 0" -Wait -NoNewWindow

Start-Process "powercfg.exe" -ArgumentList "-SetActive SCHEME_CURRENT" -Wait -NoNewWindow
Add-Check "Power Settings Configured" "OK"

# BitLocker Backup & Suspend
try {
    $bl = Get-BitLockerVolume -MountPoint "C:" -ErrorAction SilentlyContinue
    if ($bl) {
        $kp = $bl.KeyProtector | Where-Object { $_.KeyProtectorType -eq 'RecoveryPassword' } | Select-Object -First 1
        if (-not $kp) {
            Add-BitLockerKeyProtector -MountPoint "C:" -RecoveryPasswordProtector -ErrorAction SilentlyContinue | Out-Null
            $bl = Get-BitLockerVolume -MountPoint "C:" -ErrorAction SilentlyContinue
            $kp = $bl.KeyProtector | Where-Object { $_.KeyProtectorType -eq 'RecoveryPassword' } | Select-Object -First 1
        }
        
        if ($kp) {
            $identifier = $kp.KeyProtectorId
            $recoveryPassword = $kp.RecoveryPassword
            
            $keysDir = Join-Path $scriptDir "BitLockerKeys"
            if (-not (Test-Path $keysDir)) { New-Item -ItemType Directory -Path $keysDir | Out-Null }
            
            $fileName = "${newPCName}_BitLocker 回復キー ${identifier}.txt"
            $filePath = Join-Path $keysDir $fileName
            
            $keyContent = @"
BitLocker ドライブ暗号化回復キー

回復キーは、BitLocker で暗号化されたドライブのロックを解除するために使用します。

回復キーの識別子: $identifier

回復キー:
$recoveryPassword
"@
            Set-Content -Path $filePath -Value $keyContent -Encoding UTF8
            Add-Check "BitLocker Key Exported" "OK"
        }
        
        # 保護の中断 (Suspend)
        Suspend-BitLocker -MountPoint "C:" -RebootCount 0 -ErrorAction SilentlyContinue | Out-Null
        Add-Check "BitLocker Suspended" "OK"
    } else {
        Add-Check "BitLocker Backup & Suspend" "Skip (Not supported)"
    }
} catch { Add-Check "BitLocker Operations" "NG" }

# Manufacturer specific
$manufacturer = (Get-CimInstance Win32_ComputerSystem).Manufacturer
switch -Wildcard ($manufacturer) {
    "*HP*" {
        $hpServices = @("HpTouchpointAnalyticsService", "hpsvcsscan", "HPDiagsCap", "HPAppHelperCap", "HPNetworkCap")
        foreach ($svc in $hpServices) {
            Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
        }
        Add-Check "HP Services Disabled" "OK"
    }
    "*Fujitsu*" {
        $fjServices = @("Fuj02e3DriverUtilityService", "FBIOSDRVService")
        foreach ($svc in $fjServices) {
            Set-Service -Name $svc -StartupType Manual -ErrorAction SilentlyContinue
        }
        Add-Check "Fujitsu Services to Manual" "OK"
    }
}

# =========================================
# 4. Apply User Preferences (HKCU and Defaults)
# =========================================
try {
    # Storage Sense OFF
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy" -Name "01" -Value 0 -Force
    Add-Check "Storage Sense OFF" "OK"

    # Snap Assist OFF (完全無効化)
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WindowArrangementActive" -Value "0" -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "SnapAssist" -Value 0 -Force
    Add-Check "Snap Assist OFF" "OK"

    # Alt+Tab & Virtual Desktops (20 tabs, All Desktops)
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "MultiTaskingAltTabFilter" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "VirtualDesktopTaskbarFilter" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "VirtualDesktopAltTabFilter" -Value 0 -Force
    Add-Check "Alt+Tab and Virtual Desktop Settings" "OK"

    # Clipboard History OFF
    if (-not (Test-Path "HKCU:\Software\Microsoft\Clipboard")) { New-Item -Path "HKCU:\Software\Microsoft\Clipboard" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Clipboard" -Name "EnableClipboardHistory" -Value 0 -Force
    Add-Check "Clipboard History OFF" "OK"

    # Visual Effects Set to Custom (パフォーマンス: カスタム指定)
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Value 3 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "IconsOnly" -Value 0 -Force # 縮小版表示
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ListviewShadow" -Value 1 -Force # アイコン名に影
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ListviewAlphaSelect" -Value 0 -Force # 半透明の[選択]ツールをオフ
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "DragFullWindows" -Value 1 -Force # ドラッグ中に内容表示
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "FontSmoothing" -Value 2 -Force # フォント縁滑らか
    Add-Check "Visual Effects Custom Configured" "OK"

    # Desktop Icons Configured
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel" -Name "{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel" -Name "{20D04FE0-3AEA-1069-A2D8-08002B30309D}" -Value 0 -Force
    Add-Check "Desktop Icons Configured" "OK"

    # Notifications OFF
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications" -Name "ToastEnabled" -Value 0 -Force
    Add-Check "Notifications OFF" "OK"

    # Recent Items / Start Menu Recommended OFF
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Start_ShowRecentDocs" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Start_TrackDocs" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Start_TrackProgs" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer" -Name "ShowRecent" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer" -Name "ShowFrequent" -Value 0 -Force
    Add-Check "Recent Items and Start Recommended OFF" "OK"

    # Keyboard / Mouse Speed
    if (-not (Test-Path "HKCU:\Control Panel\Keyboard")) { New-Item -Path "HKCU:\Control Panel\Keyboard" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Control Panel\Keyboard" -Name "KeyboardDelay" -Value "0" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Keyboard" -Name "KeyboardSpeed" -Value "31" -Force
    Add-Check "Keyboard Speed Configured" "OK"

} catch { Add-Check "User Preferences" "NG" }

# Disk Defrag
try {
    Optimize-Volume -DriveLetter C -Defrag -ErrorAction SilentlyContinue | Out-Null
    Add-Check "Disk Defrag Executed" "OK"
} catch { Add-Check "Disk Defrag Executed" "NG" }

# =========================================
# 5. Apply Individual Data
# =========================================
if ($newPCName -ne $currentPCName) {
    Rename-Computer -NewName $newPCName -Force -ErrorAction SilentlyContinue
    Add-Check "PC Name Changed" "OK"
}

# Network Settings
if ($setStaticIP -match "^y" -and -not [string]::IsNullOrWhiteSpace($ipAddress)) {
    $adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.MacAddress } | Select-Object -First 1
    if ($adapter) {
        $prefix = ($subnetMask.Split('.').Where({$_ -ne '0'}).Count * 8)
        New-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -IPAddress $ipAddress -PrefixLength $prefix -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
        
        $dnsServers = @()
        if (-not [string]::IsNullOrWhiteSpace($dns1)) { $dnsServers += $dns1 }
        if (-not [string]::IsNullOrWhiteSpace($dns2)) { $dnsServers += $dns2 }
        if ($dnsServers.Count -gt 0) {
            Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses $dnsServers -ErrorAction SilentlyContinue | Out-Null
        }
        Add-Check "Static IP and DNS Set" "OK"
    } else {
        Add-Check "Static IP Set" "NG"
    }
}

# Wi-Fi Profile
if ($setWifi -match "^y") {
    $xmlPath = Join-Path $env:TEMP "WLANProfile.xml"
    $xmlContent = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>$wifiSSID</name>
    <SSIDConfig>
        <SSID>
            <name>$wifiSSID</name>
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
                <keyMaterial>$wifiPass</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"@
    Set-Content -Path $xmlPath -Value $xmlContent -Encoding UTF8
    Start-Process "netsh" -ArgumentList "wlan add profile filename=`"$xmlPath`"" -Wait -NoNewWindow
    Start-Process "netsh" -ArgumentList "wlan connect name=`"$wifiSSID`"" -Wait -NoNewWindow
    Remove-Item -Path $xmlPath -Force -ErrorAction SilentlyContinue
    Add-Check "Wi-Fi Configured" "OK"
}

if (-not [string]::IsNullOrWhiteSpace($targetUser)) {
    $userObj = Get-LocalUser -Name $targetUser -ErrorAction SilentlyContinue
    $secPass = ConvertTo-SecureString $targetPass -AsPlainText -Force
    if (-not $userObj) {
        New-LocalUser -Name $targetUser -Password $secPass -FullName $targetUser -Description "OA Terminal Admin" | Out-Null
        Add-LocalGroupMember -Group "Administrators" -Member $targetUser -ErrorAction SilentlyContinue | Out-Null
    } else {
        Set-LocalUser -Name $targetUser -Password $secPass
    }
    Set-LocalUser -Name $targetUser -PasswordNeverExpires $true
    Add-Check "User Configured" "OK"
}

# =========================================
# 6. Application Installation (V2 Merged)
# =========================================
$InstallersDir = Join-Path $scriptDir "Installers"
if (Test-Path $InstallersDir) {
    Write-Host "`nアプリの自動インストールを開始します..." -ForegroundColor Yellow
    $appList = @("Office365", "7-Zip", "AcrobatReader", "Chrome", "ESET", "Sky")
    foreach ($appName in $appList) {
        $appDir = Join-Path $InstallersDir $appName
        if (-not (Test-Path $appDir)) { continue }
        
        $exeFile = Get-ChildItem -Path $appDir -Filter "*.exe" | Select-Object -First 1
        $msiFile = Get-ChildItem -Path $appDir -Filter "*.msi" | Select-Object -First 1
        $batFile = Get-ChildItem -Path $appDir -Filter "*.bat" | Select-Object -First 1
        
        if (-not ($exeFile -or $msiFile -or $batFile)) { continue }
        
        Write-Host " -> $appName をインストール中..." -ForegroundColor Cyan
        
        if ($batFile) {
            $process = Start-Process -FilePath cmd.exe -ArgumentList "/c `"$($batFile.FullName)`"" -Wait -NoNewWindow -PassThru -WorkingDirectory $appDir
            if ($process.ExitCode -eq 0) { Add-Check "Install $appName" "OK" } else { Add-Check "Install $appName" "NG" }
        }
        elseif ($msiFile) {
            $process = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$($msiFile.FullName)`" /qn /norestart" -Wait -PassThru -WorkingDirectory $appDir
            if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) { Add-Check "Install $appName" "OK" } else { Add-Check "Install $appName" "NG" }
        }
        elseif ($exeFile) {
            $arguments = "/S"
            if ($exeFile.Name -match "AcroRdr") { $arguments = "/sAll /rs /msi EULA_ACCEPT=YES" }
            elseif ($exeFile.Name -match "ees_nt64|avremover") { $arguments = "--quiet --accepteula /S /silent" }
            elseif ($exeFile.Name -match "setup" -and (Test-Path "$appDir\configuration*.xml")) {
                $xmlFile = Get-ChildItem -Path $appDir -Filter "configuration*.xml" | Select-Object -First 1
                $arguments = "/configure `"$($xmlFile.Name)`""
            }
            elseif ($exeFile.Name -match "SKYSEA") { $arguments = "/S /v`"/qn`"" }
            
            $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $arguments -Wait -PassThru -WorkingDirectory $appDir
            if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) { Add-Check "Install $appName" "OK" } else { Add-Check "Install $appName" "NG" }
        }
    }
}

$checklist | Out-File $ChecklistFile -Encoding UTF8

Write-Host "`nAll Kitting Steps Completed!" -ForegroundColor Green
Write-Host "Please RESTART THE PC to apply changes." -ForegroundColor Yellow
Read-Host "Press Enter to exit..."
