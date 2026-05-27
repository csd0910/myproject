<#
.SYNOPSIS
PCデータ移行ツール (バックアップ/リストア/クリーンアップ)

.DESCRIPTION
旧PCからNASへユーザーデータをバックアップし、
新PCでNASからデータをリストアするためのスクリプトです。
初心者にも分かりやすい対話型（メニュー形式）で動作します。
追加機能（Cドライブ野良フォルダ警告、容量チェック、14日経過自動削除）実装版。
#>

$ErrorActionPreference = "Stop"

# ==========================================
# 設定値 (環境に合わせて変更可能)
# ==========================================
$NAS_UNC = "\\10.85.33.230\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\PCデータ移行用"
$NAS_USER = "frt_user"
$NAS_PASS = "Forest0720@"

# 標準の移行対象フォルダ
$TargetFolders = @("Desktop", "Downloads", "Documents", "Pictures", "Music", "Videos")

# Cドライブ直下の「OS標準フォルダ」リスト（野良フォルダ判定で除外するもの）
# ※隠しフォルダ等も含む一般的なものを網羅
$SystemFolders = @(
    "PerfLogs", "Program Files", "Program Files (x86)", "Users", "Windows",
    "Intel", "Recovery", "`$Recycle.Bin", "System Volume Information", "ProgramData",
    "Documents and Settings", "MSOCache", "swsetup", "ESD"
)

# ==========================================
# 共通関数群
# ==========================================

# 1. ネットワークドライブ（NAS）への接続処理
function Connect-NAS {
    Write-Host "NASへの接続を確認・確立しています..." -ForegroundColor Cyan
    
    $Y_Path = "Y:\システム統括部\業改室\★大宮システム部\（NAS）伊藤\PCデータ移行用"
    if (Test-Path $Y_Path) {
        Write-Host "既存のYドライブ経由でのアクセスを確認しました。" -ForegroundColor Green
        return $Y_Path
    }

    if (Test-Path $NAS_UNC) {
        Write-Host "既存のネットワーク接続を検知しました。" -ForegroundColor Green
        return $NAS_UNC
    }

    $cmd = "net use `"$NAS_UNC`" `"$NAS_PASS`" /user:`"$NAS_USER`""
    Invoke-Expression $cmd | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "NASへの接続に失敗しました。すでに別のユーザー名でサーバーに接続されている可能性があります。"
        Write-Warning "PCを再起動するか、手動でエクスプローラーからNASへアクセスできるか確認してください。"
        Pause
        exit
    }
    Write-Host "NASへの認証を一時的に確立しました。" -ForegroundColor Green
    return $NAS_UNC
}

# フォルダの合計サイズを計算する関数
function Get-FolderSizeGB ($PathList) {
    $totalBytes = 0
    foreach ($path in $PathList) {
        if (Test-Path $path) {
            # アクセス拒否エラー等を無視してファイルサイズを集計
            $items = Get-ChildItem -Path $path -Recurse -File -Force -ErrorAction SilentlyContinue
            foreach ($item in $items) {
                $totalBytes += $item.Length
            }
        }
    }
    return [math]::Round($totalBytes / 1GB, 2)
}

# 2. バックアップ実行処理 (旧PC向け)
function Start-Backup ($NasRootPath) {
    Write-Host ""
    Write-Host "【バックアップ前の事前チェック】" -ForegroundColor Yellow
    
    # ---------------------------------------------------------
    # (A) Cドライブ直下の野良フォルダ検知
    # ---------------------------------------------------------
    $cDriveDirs = Get-ChildItem -Path "C:\" -Directory -Force -ErrorAction SilentlyContinue
    $customDirs = @()
    foreach ($dir in $cDriveDirs) {
        if ($SystemFolders -notcontains $dir.Name) {
            $customDirs += $dir.FullName
        }
    }

    $AdditionalPaths = @()
    if ($customDirs.Count -gt 0) {
        Write-Warning "Cドライブ直下に標準外の独自のフォルダ（野良フォルダ）が検出されました！"
        Write-Host "検出されたフォルダ:" -ForegroundColor Cyan
        $customDirs | ForEach-Object { Write-Host " - $_" }
        Write-Host "これらは標準の移行対象（DesktopやDocuments等）には含まれていません。"
        
        $addReq = Read-Host "バックアップに追加したいフォルダパスがあれば、入力してください（複数ある場合はカンマ「,」で区切る。追加しない場合はそのままEnter）"
        if (-not [string]::IsNullOrWhiteSpace($addReq)) {
            $paths = $addReq -split ","
            foreach ($p in $paths) {
                $trimmed = $p.Trim()
                if (Test-Path $trimmed) {
                    $AdditionalPaths += $trimmed
                    Write-Host "追加対象としてセットしました: $trimmed" -ForegroundColor Green
                } else {
                    Write-Warning "パスが見つかりませんでした。スキップします: $trimmed"
                }
            }
        }
    }

    # ---------------------------------------------------------
    # (B) 容量チェック (事前警告)
    # ---------------------------------------------------------
    Write-Host "バックアップ対象のデータ容量を計算しています... (少々お待ちください)" -ForegroundColor Cyan
    $allSourcePaths = @()
    foreach ($folder in $TargetFolders) {
        $allSourcePaths += Join-Path $env:USERPROFILE $folder
    }
    $allSourcePaths += $AdditionalPaths

    $totalGB = Get-FolderSizeGB -PathList $allSourcePaths
    Write-Host ("バックアップ予定の合計サイズ: 約 {0} GB" -f $totalGB) -ForegroundColor Yellow

    if ($totalGB -gt 30) {
        Write-Warning "データ容量が 30GB を超えています！"
        Write-Warning "ネットワークやNASの容量を圧迫し、移行に時間がかかる可能性があります。"
        Write-Warning "Downloadsフォルダ内の不要なISOファイルや動画、または古いPSTファイル等の削除を推奨します。"
        
        $ans = Read-Host "このままバックアップを続行しますか？ (Y/N)"
        if ($ans -notmatch "^[Yy]$") {
            Write-Host "バックアップをキャンセルしました。"
            return
        }
    }

    # ---------------------------------------------------------
    # (C) 実際のバックアップ処理
    # ---------------------------------------------------------
    $DateStr = Get-Date -Format "yyyyMMdd"
    $BackupDirName = "$env:COMPUTERNAME`_$DateStr`_backup"
    $BackupFullPath = Join-Path $NasRootPath $BackupDirName
    
    Write-Host ""
    Write-Host "【バックアップ開始】" -ForegroundColor Yellow
    Write-Host "保存先: $BackupFullPath"
    
    if (-not (Test-Path $BackupFullPath)) {
        New-Item -ItemType Directory -Path $BackupFullPath | Out-Null
    }

    $LogPath = Join-Path $BackupFullPath "BackupLog_$DateStr.txt"

    # コピー処理用の共通関数（標準フォルダと追加フォルダの両方で使う）
    function Run-Robocopy($src, $dst, $log) {
        $robocopyArgs = @(
            "`"$src`"",
            "`"$dst`"",
            "/E",
            "/COPY:DT", "/DCOPY:T", "/FFT", # エラー5回避オプション
            "/R:1", "/W:1",
            "/XF", "desktop.ini", "Thumbs.db", "*.lnk",
            "/MT:4",
            "/LOG+:`"$log`"",
            "/TEE"
        )
        & robocopy $robocopyArgs
    }

    # 1. 標準フォルダのコピー
    foreach ($folder in $TargetFolders) {
        $SourcePath = Join-Path $env:USERPROFILE $folder
        $DestPath = Join-Path $BackupFullPath $folder
        
        if (Test-Path $SourcePath) {
            Write-Host "[コピー中] $folder ..." -ForegroundColor Cyan
            Run-Robocopy $SourcePath $DestPath $LogPath
        }
    }

    # 2. 追加フォルダのコピー
    foreach ($addPath in $AdditionalPaths) {
        $folderName = Split-Path $addPath -Leaf
        $DestPath = Join-Path $BackupFullPath "Custom_$folderName"
        
        if (Test-Path $addPath) {
            Write-Host "[コピー中(追加分)] $addPath ..." -ForegroundColor Cyan
            Run-Robocopy $addPath $DestPath $LogPath
        }
    }
    
    Write-Host ""
    Write-Host "バックアップが完了しました！" -ForegroundColor Green
    Write-Host "ログファイル: $LogPath" -ForegroundColor Green
}

# 3. リストア実行処理 (新PC向け)
function Start-Restore ($NasRootPath) {
    Write-Host ""
    Write-Host "【リストア開始】" -ForegroundColor Yellow
    
    $BackupFolders = Get-ChildItem -Path $NasRootPath -Directory -Filter "*_backup"
    if ($BackupFolders.Count -eq 0) {
        Write-Warning "NAS上にバックアップフォルダが見つかりません。"
        return
    }

    Write-Host "NAS上のバックアップデータ一覧:"
    for ($i = 0; $i -lt $BackupFolders.Count; $i++) {
        Write-Host ("[{0}] {1}" -f ($i + 1), $BackupFolders[$i].Name)
    }
    
    $selection = Read-Host "復元するフォルダの番号を入力してください (キャンセルは Enter)"
    if ([string]::IsNullOrWhiteSpace($selection) -or $selection -notmatch '^\d+$') {
        Write-Host "キャンセルしました。"
        return
    }
    
    $idx = [int]$selection - 1
    if ($idx -lt 0 -or $idx -ge $BackupFolders.Count) {
        Write-Warning "無効な番号です。"
        return
    }

    $SelectedBackupPath = $BackupFolders[$idx].FullName
    $DateStr = Get-Date -Format "yyyyMMdd"
    $LogPath = Join-Path $env:USERPROFILE "Desktop\RestoreLog_$DateStr.txt"

    Write-Host ""
    Write-Host "以下のデータをこのPCに復元します。" -ForegroundColor Yellow
    Write-Host "復元元: $SelectedBackupPath"
    
    $confirm = Read-Host "本当によろしいですか？ (Y/N)"
    if ($confirm -notmatch "^[Yy]$") {
        Write-Host "キャンセルしました。"
        return
    }

    # リストアでもエラー回避のコピーオプションを利用
    function Run-RobocopyRestore($src, $dst, $log) {
        $robocopyArgs = @(
            "`"$src`"",
            "`"$dst`"",
            "/E",
            "/COPY:DT", "/DCOPY:T", "/FFT",
            "/R:1", "/W:1",
            "/XF", "desktop.ini", "Thumbs.db", "*.lnk",
            "/MT:4",
            "/LOG+:`"$log`"",
            "/TEE"
        )
        & robocopy $robocopyArgs
    }

    # 標準フォルダのリストア
    foreach ($folder in $TargetFolders) {
        $SourcePath = Join-Path $SelectedBackupPath $folder
        $DestPath = Join-Path $env:USERPROFILE $folder
        
        if (Test-Path $SourcePath) {
            Write-Host "[復元中] $folder ..." -ForegroundColor Cyan
            Run-RobocopyRestore $SourcePath $DestPath $LogPath
        }
    }

    # カスタムフォルダのリストア（注意喚起のみ・自動ではC直下に戻さない）
    $customBackups = Get-ChildItem -Path $SelectedBackupPath -Directory -Filter "Custom_*"
    if ($customBackups.Count -gt 0) {
        Write-Host ""
        Write-Warning "※ バックアップ元に「追加の独自フォルダ」が含まれています。"
        foreach ($cb in $customBackups) {
            Write-Host " - $($cb.Name)"
        }
        Write-Host "これらは自動でCドライブ直下には復元されません。NASから手動で必要な場所にコピーしてください。"
    }
    
    Write-Host ""
    Write-Host "リストア（復元）が完了しました！" -ForegroundColor Green
    Write-Host "デスクトップにログファイル ($LogPath) を出力しました。" -ForegroundColor Green
}

# 4. [管理者用] 古いバックアップの削除 (14日経過)
function Clean-OldBackups ($NasRootPath) {
    Write-Host ""
    Write-Host "【14日経過したバックアップデータのクリーンアップ】" -ForegroundColor Yellow
    
    $limitDate = (Get-Date).AddDays(-14)
    Write-Host "基準日: $($limitDate.ToString('yyyy/MM/dd')) 以前のデータを検索します..."
    
    $oldFolders = Get-ChildItem -Path $NasRootPath -Directory -Filter "*_backup" | Where-Object {
        # フォルダの作成日時または更新日時が基準日より古いものを対象
        $_.CreationTime -lt $limitDate -and $_.LastWriteTime -lt $limitDate
    }

    if ($oldFolders.Count -eq 0) {
        Write-Host "14日以上経過した古いバックアップフォルダは見つかりませんでした。" -ForegroundColor Green
        return
    }

    Write-Host "以下のフォルダが削除対象です：" -ForegroundColor Red
    foreach ($folder in $oldFolders) {
        Write-Host (" - {0} (更新日: {1})" -f $folder.Name, $folder.LastWriteTime.ToString('yyyy/MM/dd'))
    }

    $ans = Read-Host "これらのフォルダをNASから【完全に削除】します。よろしいですか？ (Y/N)"
    if ($ans -match "^[Yy]$") {
        foreach ($folder in $oldFolders) {
            Write-Host "$($folder.Name) を削除中..." -ForegroundColor Cyan
            Remove-Item -Path $folder.FullName -Recurse -Force
        }
        Write-Host "クリーンアップが完了しました。" -ForegroundColor Green
    } else {
        Write-Host "削除をキャンセルしました。"
    }
}

# ==========================================
# メインメニュー
# ==========================================
function Show-Menu {
    Clear-Host
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host " PCデータ移行ツール (Ver 2.0)" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host " 1: [旧PC] データをNASにバックアップする"
    Write-Host " 2: [新PC] NASからデータをリストア（復元）する"
    Write-Host " 3: [管理者] NASの古いデータ(14日経過)を削除"
    Write-Host " 4: 終了する"
    Write-Host "==========================================" -ForegroundColor Cyan
    
    $choice = Read-Host "実行したい番号を入力してください"
    
    switch ($choice) {
        "1" {
            $basePath = Connect-NAS
            Start-Backup -NasRootPath $basePath
        }
        "2" {
            $basePath = Connect-NAS
            Start-Restore -NasRootPath $basePath
        }
        "3" {
            $basePath = Connect-NAS
            Clean-OldBackups -NasRootPath $basePath
        }
        "4" {
            Write-Host "終了します。"
            exit
        }
        default {
            Write-Warning "1〜4の番号を入力してください。"
        }
    }
    
    Write-Host ""
    Read-Host "Enterキーを押すとメニューに戻ります..."
    Show-Menu
}

# 処理開始
Show-Menu
