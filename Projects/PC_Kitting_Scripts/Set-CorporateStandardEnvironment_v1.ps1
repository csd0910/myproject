<#
.SYNOPSIS
OA端末 統合キッティング自動化ツール (Ver.1: 設定変更フェーズ)
.DESCRIPTION
このスクリプトは、キッティング手順（設定変更、不要サービス停止、メーカー差分吸収）を自動化します。
実行時に必要な個別情報（ユーザー名、パスワード、IPアドレス等）を最初に入力させます。
#>

# =========================================
# 1. 管理者権限のチェックと再起動
# =========================================
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "管理者権限で実行していません。管理者として再起動します..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " OA端末 自動キッティングツール [Ver.1: 設定変更フェーズ]" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# =========================================
# 2. 個別設定情報の手動入力 (UIフェーズ)
# =========================================
Write-Host "【初期設定情報の入力】" -ForegroundColor Green

# ① PC名
$currentPCName = $env:COMPUTERNAME
$newPCName = Read-Host "▶ 1. 設定するPC名を入力してください (現在の名前を維持する場合はそのままEnter) [$currentPCName]"
if ([string]::IsNullOrWhiteSpace($newPCName)) { $newPCName = $currentPCName }

# ② ローカルユーザー作成/パスワード
$targetUser = Read-Host "▶ 2. 作成・設定するローカルユーザー名を入力してください (例: SysAdmin)"
if (-not [string]::IsNullOrWhiteSpace($targetUser)) {
    $targetPass = Read-Host "▶ 3. 上記ユーザーのサインイン用パスワードを入力してください (パスワードは画面に表示されます)"
}

# ③ ネットワーク設定（IPアドレス等）
$setStaticIP = Read-Host "▶ 4. 固定IPアドレス(NWアドレス)を設定しますか？ (y/n) [n]"
if ($setStaticIP -match "^y") {
    $ipAddress = Read-Host "   - IPアドレスを入力してください (例: 192.168.1.50)"
    $subnetMask = Read-Host "   - サブネットマスクを入力してください (空白で 255.255.255.0)"
    if ([string]::IsNullOrWhiteSpace($subnetMask)) { $subnetMask = "255.255.255.0" }
    $gateway = Read-Host "   - デフォルトゲートウェイを入力してください (空白で設定なし)"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 入力内容の確認"
Write-Host "   PC名         : $newPCName"
Write-Host "   ユーザー名   : $targetUser"
Write-Host "   NWアドレス設定: $(if($setStaticIP -match '^y') { $ipAddress } else { 'DHCP (変更なし)' })"
Write-Host "============================================================" -ForegroundColor Cyan
$confirm = Read-Host "この内容で自動設定を開始してよろしいですか？ (y/n)"
if ($confirm -notmatch "^y") {
    Write-Host "処理を中断しました。" -ForegroundColor Red
    Read-Host "Enterキーで終了します..."
    exit
}

Write-Host "`n自動設定を開始します。しばらくお待ちください..." -ForegroundColor Cyan

# =========================================
# 3. メーカー判定と固有サービスの無効化
# =========================================
$sysInfo = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$manufacturer = $sysInfo.Manufacturer

Write-Host "[*] メーカー判定: $manufacturer" -ForegroundColor Yellow

switch -Wildcard ($manufacturer) {
    "*HP*" {
        Write-Host "   -> HP製端末の不要サービスを停止します..."
        $hpServices = @("HpTouchpointAnalyticsService", "hpsvcsscan", "HPDiagsCap", "HPAppHelperCap", "HPNetworkCap")
        foreach ($svc in $hpServices) {
            if (Get-Service $svc -ErrorAction SilentlyContinue) {
                Set-Service -Name $svc -StartupType Disabled
                Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
                Write-Host "      無効化完了: $svc"
            }
        }
    }
    "*Fujitsu*" {
        Write-Host "   -> 富士通製端末の不要サービスを停止します..."
        # ハードウェア依存のため手動に切り替えるなど安全に倒す
        $fjServices = @("Fuj02e3DriverUtilityService", "FBIOSDRVService")
        foreach ($svc in $fjServices) {
            if (Get-Service $svc -ErrorAction SilentlyContinue) {
                Set-Service -Name $svc -StartupType Manual
                Write-Host "      手動起動に変更: $svc"
            }
        }
    }
    Default {
        Write-Host "   -> 固有のメーカー無効化処理はスキップされました。"
    }
}

# =========================================
# 4. 全社共通ポリシー（キッティング基本設定）適用
# =========================================
Write-Host "[*] 共通システム設定を適用中..." -ForegroundColor Yellow

try {
    # 4-1. UACの無効化
    Write-Host "   - UAC(ユーザーアカウント制御)の無効化"
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 0 -Force

    # 4-2. ハイバネーション(休止状態)の無効化
    Write-Host "   - 休止状態の無効化"
    Start-Process "powercfg.exe" -ArgumentList "/hibernate off" -Wait -NoNewWindow

    # 4-3. NTPサーバー設定
    Write-Host "   - NTPサーバーを ntp.nict.jp に変更"
    Start-Process "w32tm" -ArgumentList "/config /manualpeerlist:ntp.nict.jp /syncfromflags:manual /update" -Wait -NoNewWindow
    Start-Process "net" -ArgumentList "stop w32time" -Wait -NoNewWindow
    Start-Process "net" -ArgumentList "start w32time" -Wait -NoNewWindow

    # 4-4. リモートデスクトップ有効化
    Write-Host "   - リモートデスクトップの有効化"
    Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0 -Force
    Enable-NetFirewallRule -DisplayGroup "リモート デスクトップ" -ErrorAction SilentlyContinue | Out-Null

    # 4-5. サービスの停止 (Windows Search, ICS)
    Write-Host "   - 不要機能(Windows Search等)の停止"
    Set-Service -Name "WSearch" -StartupType Disabled -ErrorAction SilentlyContinue
    Stop-Service -Name "WSearch" -Force -ErrorAction SilentlyContinue
    Set-Service -Name "SharedAccess" -StartupType Disabled -ErrorAction SilentlyContinue # ICS

    # 4-6. 電源設定 (電源ボタン押下時＝シャットダウン)
    Write-Host "   - 電源ボタンの設定を変更"
    # GUID 4f971e89-eebd-4455-a8de-9e59040e7347 (電源ボタンのアクション) -> 3 (シャットダウン)
    Start-Process "powercfg.exe" -ArgumentList "-setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 7648efa3-dd9c-4e3e-b566-50f929386280 3" -Wait -NoNewWindow
    Start-Process "powercfg.exe" -ArgumentList "-setdcvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 7648efa3-dd9c-4e3e-b566-50f929386280 3" -Wait -NoNewWindow
    Start-Process "powercfg.exe" -ArgumentList "-SetActive SCHEME_CURRENT" -Wait -NoNewWindow

} catch {
    Write-Host "共通設定適用中にエラーが発生しました: $_" -ForegroundColor Red
}

# =========================================
# 5. 個別情報（PC名、NW、ユーザー）の反映
# =========================================
Write-Host "[*] 入力された個別情報を反映中..." -ForegroundColor Yellow

# PC名の変更
if ($newPCName -ne $currentPCName) {
    Write-Host "   - PC名を [$newPCName] に変更します"
    Rename-Computer -NewName $newPCName -Force -ErrorAction SilentlyContinue
}

# ネットワーク設定
if ($setStaticIP -match "^y") {
    Write-Host "   - 固定IPアドレス ($ipAddress) を設定します"
    # 一番アクティブなイーサネットまたはWi-Fiアダプターを取得して適用
    $adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.MacAddress } | Select-Object -First 1
    if ($adapter) {
        New-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex -IPAddress $ipAddress -PrefixLength ($subnetMask.Split('.').Where({$_ -ne '0'}).Count * 8) -DefaultGateway $gateway -ErrorAction SilentlyContinue | Out-Null
    } else {
        Write-Host "     [!] アクティブなネットワークアダプタが見つかりませんでした" -ForegroundColor Red
    }
}

# ローカルユーザーの作成とパスワード無期限化
if (-not [string]::IsNullOrWhiteSpace($targetUser)) {
    Write-Host "   - ユーザー [$targetUser] の設定"
    $userObj = Get-LocalUser -Name $targetUser -ErrorAction SilentlyContinue
    $secPass = ConvertTo-SecureString $targetPass -AsPlainText -Force
    if (-not $userObj) {
        # 新規作成
        New-LocalUser -Name $targetUser -Password $secPass -FullName $targetUser -Description "OA Terminal Admin" | Out-Null
        Add-LocalGroupMember -Group "Administrators" -Member $targetUser | Out-Null
    } else {
        # パスワード変更
        Set-LocalUser -Name $targetUser -Password $secPass
    }
    # パスワード無期限化
    Set-LocalUser -Name $targetUser -PasswordNeverExpires $true
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " [完了] Ver.1 システム設定のキッティングが終了しました。" -ForegroundColor Green
Write-Host " ※PC名やUACの変更を適用するため、PCの再起動が必要です。" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

Read-Host "Enterキーを押して画面を閉じます..."
