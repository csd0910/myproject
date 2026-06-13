<#
.SYNOPSIS
  AppUpdateCheck - システム運営課 アプリ自動更新ツール
  完全サイレントモード + NAS未接続時のログ自動転送機能付き
  ポップアップを使いたい場合は「# POPUP:」のコメントを外す
#>
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$AppList = @(
    @{ Name = "Microsoft Edge";  Search = "Microsoft Edge";  WingetId = "Microsoft.Edge";              NativeTaskName = "MicrosoftEdgeUpdateTaskMachineUA" }
    @{ Name = "Google Chrome";   Search = "Google Chrome";   WingetId = "Google.Chrome.EXE";           NativeTaskName = "GoogleUpdateTaskMachineUA" }
    @{ Name = "Firefox";         Search = "Mozilla Firefox"; WingetId = "Mozilla.Firefox";             NativeTaskName = "" }
    @{ Name = "Vivaldi";         Search = "Vivaldi";         WingetId = "VivaldiTechnologies.Vivaldi"; NativeTaskName = "" }
    @{ Name = "Thunderbird";     Search = "Thunderbird";     WingetId = "Mozilla.Thunderbird";         NativeTaskName = "" }
    @{ Name = "Acrobat Reader";  Search = "Acrobat Reader";  WingetId = "";                            NativeTaskName = "" }
    @{ Name = "7-Zip";           Search = "7-Zip";           WingetId = "7zip.7zip";                   NativeTaskName = "" }
)

$TitleText  = "システム運営課 アプリ自動更新ツール"
$HeaderText = "【システム運営課 アプリ自動更新ツール】`n`n"

$NasRoot   = "\\10.85.33.230\01_全社共有"
$NasLogDir = "\\10.85.33.230\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\AppUpdateログ"
$NasUser   = "frt_user"
$NasPass   = "Forest0720@"

# POPUP: ポップアップを使いたい場合はコメントを外す
# function Show-Popup {
#     param([string]$Title, [string]$Message, [int]$TimeoutSeconds, [string]$ButtonText)
#     $form = New-Object System.Windows.Forms.Form
#     $form.Text = $Title
#     $form.Size = New-Object System.Drawing.Size(520, 470)
#     $form.StartPosition = "Manual"
#     $form.TopMost = $true
#     $form.FormBorderStyle = "FixedDialog"
#     $form.MaximizeBox = $false
#     $form.MinimizeBox = $false
#     $form.Font = New-Object System.Drawing.Font("Meiryo UI", 9)
#     $label = New-Object System.Windows.Forms.Label
#     $label.Text = $Message
#     $label.Location = New-Object System.Drawing.Point(15, 15)
#     $label.AutoSize = $true
#     $form.Controls.Add($label)
#     $button = New-Object System.Windows.Forms.Button
#     $button.Text = $ButtonText
#     $button.Location = New-Object System.Drawing.Point(190, 380)
#     $button.Size = New-Object System.Drawing.Size(120, 30)
#     $button.DialogResult = [System.Windows.Forms.DialogResult]::OK
#     $form.Controls.Add($button)
#     $form.add_Load({
#         $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
#         $form.Location = New-Object System.Drawing.Point(
#             ($wa.Width  - $form.Width  - 10),
#             ($wa.Height - $form.Height - 10)
#         )
#     })
#     if ($TimeoutSeconds -gt 0) {
#         $timer = New-Object System.Windows.Forms.Timer
#         $timer.Interval = $TimeoutSeconds * 1000
#         $timer.add_Tick({
#             $timer.Stop()
#             $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
#             $form.Close()
#         })
#         $timer.Start()
#     }
#     return $form.ShowDialog()
# }

function Get-InstalledVersion {
    param([string]$WingetText, [string]$SearchKey)
    foreach ($line in ($WingetText -split "`r`n")) {
        if (($line -match [regex]::Escape($SearchKey)) -and ($line -notmatch '^\s*[-\\|/]\s*$')) {
            if ($line -match '(\d+\.[\d.]+)') { return $Matches[1] }
        }
    }
    return ""
}

function Get-AvailableVersion {
    param([string]$WingetText, [string]$WingetId)
    foreach ($line in ($WingetText -split "`r`n")) {
        if (($line -match [regex]::Escape($WingetId)) -and ($line -notmatch '^\s*[-\\|/]\s*$')) {
            $vers = [regex]::Matches($line, '\d+\.[\d.]+')
            if ($vers.Count -ge 2) { return $vers[1].Value }
        }
    }
    return ""
}

function Invoke-NativeUpdateTask {
    param([string]$TaskName)
    if (-not $TaskName) { return $false }
    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Start-ScheduledTask -TaskName $TaskName
        return $true
    } catch {
        return $false
    }
}

# =====================================================
# --- 0. NAS認証（最初に行い、以降の処理で使い回す）---
# =====================================================
if (-not (Test-Path $NasRoot)) {
    $null = & net use $NasRoot $NasPass /user:$NasUser /persistent:no 2>&1
}

# --- 0a. 前回NAS未接続時の退避ログをNASに転送 ---
# NASに接続できており、かつローカルに退避ログが残っている場合に自動転送して削除する
$pendingLog = "$PSScriptRoot\pending_log.txt"
if ((Test-Path $NasLogDir) -and (Test-Path $pendingLog)) {
    try {
        $uploadName = "${env:COMPUTERNAME}_offline_$(Get-Date -Format 'yyyyMMddHHmm').txt"
        $pendingContent = [System.IO.File]::ReadAllText($pendingLog, [System.Text.Encoding]::UTF8)
        $divider = "=" * 50
        $header = "${divider}`r`n■ オフライン時の退避ログ（NAS接続回復後に転送）`r`n${divider}`r`n"
        $utf8Bom = New-Object System.Text.UTF8Encoding($true)
        [System.IO.File]::WriteAllText((Join-Path $NasLogDir $uploadName), $header + $pendingContent, $utf8Bom)
        Remove-Item $pendingLog -Force
    } catch { }
}

# --- 0b. wingetソース最新化（タイムラグ縮小）---
winget source update --name winget --accept-source-agreements --disable-interactivity | Out-Null

# --- 1. winget から状態取得 ---
$installedText = winget list    --accept-source-agreements --disable-interactivity | Out-String
$upgradesText  = winget upgrade --accept-source-agreements --disable-interactivity | Out-String

$logLines           = @()
$AppsToAutoUpdate   = @()
$AppsNativeOnly     = @()
$AppsManualRequired = @()

foreach ($app in $AppList) {
    $name        = $app.Name
    $search      = $app.Search
    $id          = $app.WingetId
    $hasNative   = ($app.NativeTaskName -ne "")
    $isInstalled = $installedText -match [regex]::Escape($search)

    if (-not $isInstalled) {
        $logLines += "${name} : 未インストール"
        continue
    }

    $curVer  = Get-InstalledVersion -WingetText $installedText -SearchKey $search
    $verDisp = if ($curVer) { " (v${curVer})" } else { "" }

    if ($id -eq "") {
        $logLines += "${name} : 手動更新${verDisp}"
        $AppsManualRequired += $name
        continue
    }

    $hasUpgrade = $upgradesText -match [regex]::Escape($id)
    if ($hasUpgrade) {
        $newVer   = Get-AvailableVersion -WingetText $upgradesText -WingetId $id
        $verArrow = if ($curVer -and $newVer) { " (v${curVer} → v${newVer})" } elseif ($curVer) { " (v${curVer})" } else { "" }
        $logLines += "${name} : 更新あり${verArrow}"
        $AppsToAutoUpdate += $app
    } else {
        if ($hasNative) {
            $logLines += "${name} : 最新+固有タスク起動${verDisp}"
            $AppsNativeOnly += $app
        } else {
            $logLines += "${name} : 最新${verDisp}"
        }
    }
}

# POPUP: 事前通知ポップアップ（使う場合はコメントを外す）
# if ($AppsToAutoUpdate.Count -gt 0 -or $AppsNativeOnly.Count -gt 0) {
#     $note = "`n※「OK」を押すと裏側で更新処理を開始します。"
# } elseif ($AppsManualRequired.Count -gt 0) {
#     $note = "`n※手動更新が必要なアプリがあります。"
# } else {
#     $note = "`n※すべて最新です。「OK」を押して閉じます。"
# }
# $msg = $HeaderText + "以下のアプリの状態を確認しました：`n`n" + ($logLines -join "`n") + $note
# Show-Popup -Title $TitleText -Message $msg -TimeoutSeconds 0 -ButtonText "OK" | Out-Null

# --- 2. winget による自動更新 ---
$successApps = @()
$failApps    = @()

foreach ($app in $AppsToAutoUpdate) {
    $proc = Start-Process -FilePath "winget" `
        -ArgumentList "upgrade --id $($app.WingetId) --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity" `
        -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -eq 0) { $successApps += $app.Name } else { $failApps += $app.Name }
}

# --- 3. 固有更新タスク起動 ---
$nativeTargets = ($AppsToAutoUpdate | Where-Object { $_.NativeTaskName -ne "" }) + $AppsNativeOnly
$nativeStarted = @()

foreach ($app in $nativeTargets) {
    $ok = Invoke-NativeUpdateTask -TaskName $app.NativeTaskName
    if ($ok) { $nativeStarted += $app.Name }
}

# logLines を更新結果で修正
foreach ($n in $successApps) {
    for ($i = 0; $i -lt $logLines.Count; $i++) {
        if ($logLines[$i].StartsWith($n)) { $logLines[$i] = $logLines[$i] -replace "更新あり", "更新成功(winget)" }
    }
}
foreach ($n in $failApps) {
    for ($i = 0; $i -lt $logLines.Count; $i++) {
        if ($logLines[$i].StartsWith($n)) { $logLines[$i] = $logLines[$i] -replace "更新あり", "更新失敗(winget)" }
    }
}
foreach ($n in $nativeStarted) {
    for ($i = 0; $i -lt $logLines.Count; $i++) {
        if ($logLines[$i].StartsWith($n)) { $logLines[$i] = $logLines[$i] + " → 固有タスク起動済" }
    }
}

# POPUP: 完了通知（使う場合はコメントを外す）
# $totalAction = $successApps.Count + $failApps.Count + $nativeStarted.Count
# if ($totalAction -gt 0 -or $AppsManualRequired.Count -gt 0) {
#     $resultMsg = $HeaderText + "更新処理が完了しました。`n`n"
#     if ($successApps.Count -gt 0)   { $resultMsg += "【更新成功(winget)】`n" + ($successApps -join "`n") + "`n`n" }
#     if ($nativeStarted.Count -gt 0) { $resultMsg += "【固有更新タスク起動済】`n" + ($nativeStarted -join "`n") + "`n※バックグラウンドで最新版を確認・適用中です。`n`n" }
#     if ($failApps.Count -gt 0) {
#         $resultMsg += "【失敗(起動中など)】`n" + ($failApps -join "`n") + "`n`n"
#         $resultMsg += "※失敗したアプリは手動で「メニュー」→「ヘルプ」`n　→「更新チェック」から実行してください。`n"
#     }
#     if ($AppsManualRequired.Count -gt 0) { $resultMsg += "【手動更新が必要】`n" + ($AppsManualRequired -join "`n") + "`n" }
#     Show-Popup -Title $TitleText -Message $resultMsg -TimeoutSeconds 0 -ButtonText "OK" | Out-Null
# }

# --- 4. NASへログ書き込み ---
$computerName  = $env:COMPUTERNAME
$execDateTime  = Get-Date -Format "yyyy/MM/dd HH:mm:ss"
$fileTimestamp = Get-Date -Format "yyyyMMddHHmm"
$logFileName   = "${computerName}_${fileTimestamp}.txt"
$allFailed     = $failApps + $AppsManualRequired
$overallStatus = if ($allFailed.Count -eq 0) { "正常完了" } else { "警告あり" }
$divider       = "=" * 50

$logContent  = "${divider}`r`n"
$logContent += "■ アプリ自動更新ログ`r`n"
$logContent += "${divider}`r`n"
$logContent += "PC名      : ${computerName}`r`n"
$logContent += "実行日時  : ${execDateTime}`r`n"
$logContent += "全体状態  : ${overallStatus}`r`n"
$logContent += "${divider}`r`n"
$logContent += "【アプリ状態一覧】`r`n"
foreach ($line in $logLines) { $logContent += "  ・${line}`r`n" }
$logContent += "${divider}`r`n"

try {
    if (-not (Test-Path $NasLogDir)) {
        New-Item -ItemType Directory -Path $NasLogDir -Force | Out-Null
    }
    $utf8Bom = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText((Join-Path $NasLogDir $logFileName), $logContent, $utf8Bom)
} catch {
    # NAS書き込み失敗時はローカルに退避（次回NAS接続時に自動転送される）
    $utf8Bom = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::AppendAllText("$PSScriptRoot\pending_log.txt", $logContent, $utf8Bom)
}