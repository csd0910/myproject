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

# 1.5 Manufacturer Detection
$Manufacturer = (Get-CimInstance Win32_ComputerSystem).Manufacturer
Write-Host "`n[検出されたメーカー]: $Manufacturer" -ForegroundColor Yellow

Write-Host "`n--- [端末タイプの選択] ---" -ForegroundColor Cyan
Write-Host "1: OA端末 (標準)"
Write-Host "2: 仮想基幹端末 (Office2010/VMware/専用SKY・ESET)"
$termType = Read-Host "セットアップする端末の種類を選択してください (1 または 2) [1]"
if ([string]::IsNullOrWhiteSpace($termType)) { $termType = "1" }

# 2. Inputs
Write-Host "`n--- [初期情報入力] ---" -ForegroundColor Green
$currentPCName = $env:COMPUTERNAME
$newPCName = Read-Host "1. 新しいPC名を入力 (そのままEnterで [$currentPCName] を維持)"
if ([string]::IsNullOrWhiteSpace($newPCName)) { $newPCName = $currentPCName }

$targetUser = Read-Host "2. 作成するローカルユーザー名 (例: SysAdmin / 空白でスキップ)"
$targetPass = ""
if (-not [string]::IsNullOrWhiteSpace($targetUser)) {
    $targetPass = Read-Host "3. $targetUser のパスワード"
}

$setStaticIP = Read-Host "4. 固定IP/DNSを設定しますか？ (既に設定済み・またはDHCPなら 'n') (y/n) [n]"
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

# --- Network Configuration ---
Write-Host "`n[Network Configuration]" -ForegroundColor Cyan
if ($setStaticIP -match "^y" -and -not [string]::IsNullOrWhiteSpace($ipAddress)) {
    Write-Host "Configuring Wired IP..."
    $adapter = Get-NetAdapter | Where-Object { $_.Status -eq "Up" -and $_.MediaType -eq "802.3" } | Select-Object -First 1
    if (-not $adapter) {
        $adapter = Get-NetAdapter -InterfaceDescription "*Ethernet*", "*GbE*" | Select-Object -First 1
    }
    if ($adapter) {
        $prefix = 24
        if ($subnetMask -eq "255.255.0.0") { $prefix = 16 }
        New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $ipAddress -PrefixLength $prefix -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
        Set-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $ipAddress -PrefixLength $prefix -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
        if (-not [string]::IsNullOrWhiteSpace($dns1)) {
            $dnsServers = @($dns1)
            if (-not [string]::IsNullOrWhiteSpace($dns2)) { $dnsServers += $dns2 }
            Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ServerAddresses $dnsServers -ErrorAction SilentlyContinue | Out-Null
        }
        Add-Check "Wired IP ($ipAddress)" "OK"
    } else {
        Add-Check "Wired IP" "NG (Adapter not found)"
    }
}

# 2. Wi-Fi Configuration
if ($setWifi -match "^y" -and -not [string]::IsNullOrWhiteSpace($wifiSSID)) {
    Write-Host "Configuring Wi-Fi Profile..."
    $xml = "<?xml version=`"1.0`"?><WLANProfile xmlns=`"http://www.microsoft.com/networking/WLAN/profile/v1`"><name>$wifiSSID</name><SSIDConfig><SSID><name>$wifiSSID</name></SSID></SSIDConfig><connectionType>ESS</connectionType><connectionMode>auto</connectionMode><MSM><security><authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption><sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>$wifiPass</keyMaterial></sharedKey></security></MSM></WLANProfile>"
    $xmlPath = "$env:TEMP\wifi_profile.xml"
    $xml | Out-File -FilePath $xmlPath -Encoding UTF8
    netsh wlan add profile filename=`"$xmlPath`" | Out-Null
    netsh wlan connect name=`"$wifiSSID`" | Out-Null
    Remove-Item $xmlPath -ErrorAction SilentlyContinue
    Add-Check "Wi-Fi ($wifiSSID)" "OK"
}

# 3. NAS (Network Drive) Mapping
if ($setStaticIP -match "^y") {
    Write-Host "Mounting NAS Y: Drive..."
    $nasPath = "\\frt-nas\01_全社共有"
    $nasPathFallback = "\\10.85.33.230\01_全社共有"
    $user = "frt_user"
    $pass = "Forest0720@"
    if (Get-PSDrive Y -ErrorAction SilentlyContinue) {
        Remove-SmbMapping -LocalPath "Y:" -Force -UpdateProfile -ErrorAction SilentlyContinue
        cmd.exe /c "net use Y: /delete /y 2>NUL"
    }
    Start-Sleep -Seconds 3
    cmd.exe /c "net use Y: `"$nasPath`" /user:$user `"$pass`" /persistent:yes 2>NUL"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Trying fallback IP..." -ForegroundColor Yellow
        cmd.exe /c "net use Y: `"$nasPathFallback`" /user:$user `"$pass`" /persistent:yes 2>NUL"
    }
    if (Test-Path "Y:\") {
        $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##frt-nas#01_全社共有"
        if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
        Set-ItemProperty -Path $regPath -Name "_LabelFromReg" -Value "01_全社共有 (\\frt-nas)" -Force
        $regPathFallback = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2\##10.85.33.230#01_全社共有"
        if (-not (Test-Path $regPathFallback)) { New-Item -Path $regPathFallback -Force | Out-Null }
        Set-ItemProperty -Path $regPathFallback -Name "_LabelFromReg" -Value "01_全社共有 (\\frt-nas)" -Force
        Add-Check "NAS Y:" "OK"
    } else {
        Add-Check "NAS Y:" "NG"
    }
} else {
    Write-Host "Skipping NAS Mapping (Wired LAN skipped)" -ForegroundColor DarkGray
    Add-Check "NAS Y:" "Skipped"
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

    # Lock Screen Settings (No Apps & No Sign-In Background)
    if (-not (Test-Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization")) { New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" -Force | Out-Null }
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" -Name "NoLockScreenAppNotifications" -Value 1 -Force
    if (-not (Test-Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System")) { New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -Force | Out-Null }
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -Name "DisableLogonBackgroundImage" -Value 1 -Force
    Add-Check "Lock Screen Policies Configured" "OK"

# NTP Server (標準時刻同期の構成)
$serversPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DateTime\Servers"
if (-not (Test-Path $serversPath)) { New-Item -Path $serversPath -Force | Out-Null }
Set-ItemProperty -Path $serversPath -Name "1" -Value "ntp.nict.jp" -Force
Set-ItemProperty -Path $serversPath -Name "(Default)" -Value "1" -Force
Start-Process "w32tm" -ArgumentList "/config /manualpeerlist:ntp.nict.jp /syncfromflags:manual /update" -Wait -NoNewWindow
Start-Process "net" -ArgumentList "stop w32time" -Wait -NoNewWindow
Start-Process "net" -ArgumentList "start w32time" -Wait -NoNewWindow
Add-Check "NTP Set to ntp.nict.jp" "OK"

    # Services (WSearch, ICS, SysMain)
    Set-Service -Name "WSearch" -StartupType Disabled -ErrorAction SilentlyContinue
    Stop-Service -Name "WSearch" -Force -ErrorAction SilentlyContinue
    Set-Service -Name "SharedAccess" -StartupType Disabled -ErrorAction SilentlyContinue
    Stop-Service -Name "SharedAccess" -Force -ErrorAction SilentlyContinue
    Set-Service -Name "SysMain" -StartupType Disabled -ErrorAction SilentlyContinue
    Stop-Service -Name "SysMain" -Force -ErrorAction SilentlyContinue
    Add-Check "WSearch, ICS, SysMain Disabled" "OK"
    
    # Delivery Optimization (P2P Updates OFF)
    if (-not (Test-Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization")) { New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Force | Out-Null }
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -Name "DODownloadMode" -Value 0 -Force
    Add-Check "Delivery Optimization (P2P) OFF" "OK"

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
# スリープ時間 = 0分
Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 238c9fa8-0aad-41ed-83f4-97be242c8f20 29f6c1db-86da-48c5-9f15-2320c0adfc4b 0" -Wait -NoNewWindow
Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 238c9fa8-0aad-41ed-83f4-97be242c8f20 29f6c1db-86da-48c5-9f15-2320c0adfc4b 0" -Wait -NoNewWindow
# 画面の電源を切る = 0分 (必要に応じてスリープと合わせる)
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
        
        # 保護の一時停止 (Suspend)
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
    # Screensaver & Wallpaper
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveActive" -Value "1" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveTimeOut" -Value "300" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "SCRNSAVE.EXE" -Value "C:\Windows\System32\Ribbons.scr" -Force
    
    $wallpaperPath = Join-Path $scriptDir "wallpaper.jpg"
    if (Test-Path $wallpaperPath) {
        Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;
        public class Wallpaper {
            [DllImport("user32.dll", CharSet=CharSet.Auto)]
            public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
        }
"@
        [Wallpaper]::SystemParametersInfo(20, 0, $wallpaperPath, 3) | Out-Null
    }
    Add-Check "Screensaver & Wallpaper Configured" "OK"
    # Storage Sense OFF
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy" -Name "01" -Value 0 -Force
    Add-Check "Storage Sense OFF" "OK"

    # Snap Assist OFF (ウィンドウ整列)
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

    # Visual Effects Set to Custom (パフォーマンス: カスタム設定)
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Value 3 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "IconsOnly" -Value 0 -Force # 縮小版で表示
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ListviewShadow" -Value 1 -Force # アイコンに影
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ListviewAlphaSelect" -Value 0 -Force # 透明な選択矩形をオフ
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "DragFullWindows" -Value 1 -Force # ドラッグ中に内容表示
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "FontSmoothing" -Value 2 -Force # フォントなめらか
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "MenuShowDelay" -Value "20" -Force # メニュー表示速度の高速化
    
    # ----------------------------------------------------
    # メーカー別（機種別）専用チューニング
    # ----------------------------------------------------
    if ($Manufacturer -match "Dell") {
        Write-Host "Dell専用チューニング（Latitude 5320等）を適用します..." -ForegroundColor Cyan
        
        # 1. マウス・タッチパッド設定（ユーザー手動設定の反映）
        Set-ItemProperty -Path "HKCU:\Control Panel\Mouse" -Name "MouseSensitivity" -Value "20" -Force
        Set-ItemProperty -Path "HKCU:\Control Panel\Mouse" -Name "MouseWheelRouting" -Value 0 -Force
        
        # 高精度タッチパッド関連のチューニング (Dell特有)
        $precisionPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\PrecisionTouchPad"
        if (-not (Test-Path $precisionPath)) { New-Item -Path $precisionPath -Force | Out-Null }
        Set-ItemProperty -Path $precisionPath -Name "ScrollDirection" -Value 0 -Force
        
        # 2. ウィンドウ スナップ機能のオフ（手動設定の反映）
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WindowArrangementActive" -Value "0" -Force
        
        # 3. モダンスタンバイ機（DELL等）に対する電源設定に関する注記
        # ※DELLはModern Standby(S0)のため、従来のSleep設定がGUIに存在しない場合があります。
        # 必要に応じてDell OptimizerやBIOS側での設定マニュアルを併用してください。
        
    } elseif ($Manufacturer -match "FUJITSU") {
        Write-Host "富士通（FMV）専用チューニングを適用します..." -ForegroundColor Cyan
        Set-ItemProperty -Path "HKCU:\Control Panel\Mouse" -Name "MouseSensitivity" -Value "20" -Force
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WindowArrangementActive" -Value "0" -Force
    } else {
        Write-Host "汎用チューニングを適用します..." -ForegroundColor Cyan
        Set-ItemProperty -Path "HKCU:\Control Panel\Mouse" -Name "MouseSensitivity" -Value "20" -Force
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WindowArrangementActive" -Value "0" -Force
    }
    
    # 注記: アニメーション・フェード等の無効化
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarAnimations" -Value 0 -Force
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\DWM")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\DWM" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\DWM" -Name "EnableAeroPeek" -Value 0 -Force
    try {
        $upm = (Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "UserPreferencesMask" -ErrorAction SilentlyContinue).UserPreferencesMask
        if ($upm) {
            $upm[1] = $upm[1] -band 0xFD
            Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "UserPreferencesMask" -Value $upm -Force
        }
    } catch {}
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
    
    # 注記: スタートメニューの最近追加されたアプリ表示設定
    if (-not (Test-Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer")) { New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer" -Force | Out-Null }
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer" -Name "HideRecentlyAddedApps" -Value 1 -Force
    
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Start_AccountNotifications" -Value 0 -Force
    
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SubscribedContent-338388Enabled" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SubscribedContent-338389Enabled" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SystemPaneSuggestionsEnabled" -Value 0 -Force
    
    Add-Check "Recent Items and Start Recommended OFF" "OK"

    # Taskbar Settings (Search Icon, Task View OFF, Widgets OFF, Chat/Copilot OFF)
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Name "SearchboxTaskbarMode" -Value 1 -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ShowTaskViewButton" -Value 0 -Force -ErrorAction SilentlyContinue
    
    # 権限エラー(UnauthorizedAccess)が出やすいためtry-catchまたはErrorActionで無視
    try { Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarDa" -Value 0 -Force -ErrorAction Stop } catch {}
    try { Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarMn" -Value 0 -Force -ErrorAction Stop } catch {} # Chat
    try { Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ShowCopilotButton" -Value 0 -Force -ErrorAction Stop } catch {} # Copilot
    
    Add-Check "Taskbar Settings Configured" "OK"

    # Privacy & Security: Recommendations & Offers (All OFF)
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo" -Name "Enabled" -Value 0 -Force
    if (-not (Test-Path "HKCU:\Control Panel\International\User Profile")) { New-Item -Path "HKCU:\Control Panel\International\User Profile" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Control Panel\International\User Profile" -Name "HttpAcceptLanguageOptOut" -Value 1 -Force
    if (-not (Test-Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy")) { New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy" -Name "TailoredExperiencesWithDiagnosticDataEnabled" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SubscribedContent-338393Enabled" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SubscribedContent-353694Enabled" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SubscribedContent-353696Enabled" -Value 0 -Force
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" -Name "SubscribedContent-353698Enabled" -Value 0 -Force
    Add-Check "Privacy and Security Recommendations OFF" "OK"

    # Keyboard Speed
    if (-not (Test-Path "HKCU:\Control Panel\Keyboard")) { New-Item -Path "HKCU:\Control Panel\Keyboard" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Control Panel\Keyboard" -Name "KeyboardDelay" -Value "0" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Keyboard" -Name "KeyboardSpeed" -Value "31" -Force
    
    # Mouse Speed & Scroll
    if (-not (Test-Path "HKCU:\Control Panel\Mouse")) { New-Item -Path "HKCU:\Control Panel\Mouse" -Force | Out-Null }
    Set-ItemProperty -Path "HKCU:\Control Panel\Mouse" -Name "MouseSensitivity" -Value "20" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WheelScrollLines" -Value "1" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "MouseWheelRouting" -Value 0 -Force
    
    Add-Check "Keyboard & Mouse Configured" "OK"

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
    Write-Host "`nアプリのインストールを開始します..." -ForegroundColor Yellow
    
    if ($termType -eq "2") {
        # 仮想基幹端末用アプリリスト
        $appList = @("Office2010", "7-Zip", "AcrobatReader", "Chrome", "VMWare", "Sky_Kikan")
    } else {
        # OA端末用アプリリスト
        $appList = @("Office365", "7-Zip", "AcrobatReader", "Chrome", "ESET_OA", "Sky_OA")
    }
    
    foreach ($appName in $appList) {
        $appDir = Join-Path $InstallersDir $appName
        if (-not (Test-Path $appDir)) { continue }
        
        $exeFile = Get-ChildItem -Path $appDir -Filter "*.exe" | Select-Object -First 1
        $msiFile = Get-ChildItem -Path $appDir -Filter "*.msi" | Select-Object -First 1
        $batFile = Get-ChildItem -Path $appDir -Filter "*.bat" | Select-Object -First 1
        
        if (-not ($exeFile -or $msiFile -or $batFile)) { continue }
        
        # Check if already installed
        $searchName = "*"
        switch -Regex ($appName) {
            "Office2010" { $searchName = "*Office*2010*" }
            "Office365" { $searchName = "*Microsoft 365*" }
            "7-Zip" { $searchName = "*7-Zip*" }
            "AcrobatReader" { $searchName = "*Adobe Acrobat*" }
            "Chrome" { $searchName = "*Google Chrome*" }
            "VMWare" { $searchName = "*VMware Player*" }
            "ESET" { $searchName = "*ESET Endpoint*" }
            "Sky" { $searchName = "*SKYSEA*" }
        }
        $regKeys = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*")
        $installed = Get-ItemProperty $regKeys -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -and $_.DisplayName -like $searchName }
        if ($installed) {
            Write-Host " -> $appName は既にインストールされているためスキップします。" -ForegroundColor DarkCyan
            Add-Check "Install $appName" "Skipped (Already Installed)"
            continue
        }
        
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
            elseif ($appName -eq "Office2010") { $arguments = "" }
            elseif ($appName -eq "VMWare") { $arguments = "/s /v`"/qn EULAS_AGREED=1`"" }
            
            $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $arguments -Wait -PassThru -WorkingDirectory $appDir
            if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) { Add-Check "Install $appName" "OK" } else { Add-Check "Install $appName" "NG" }
        }
    }
}

$checklist | Out-File $ChecklistFile -Encoding UTF8

Write-Host "`nAll Kitting Steps Completed!" -ForegroundColor Green
Write-Host "Please RESTART THE PC to apply changes." -ForegroundColor Yellow
Read-Host "Press Enter to exit..."

