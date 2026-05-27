function Install-Applications {
    $toolRoot = Split-Path (Split-Path $MyInvocation.MyCommand.Definition -Parent) -Parent
    if ($script:KittingRoot) { $toolRoot = $script:KittingRoot }
    $localFolder = Join-Path $toolRoot "インストーラー"
    
    Write-KittingLog "インストーラー検索パス: $localFolder"
    
    if (-not (Test-Path $localFolder)) { 
        Write-KittingLog "警告: インストーラーフォルダが見つかりません。" -Level Warning
        return
    }

    # 拡張子チェック (exe, msi, bat, cmd)
    $files = Get-ChildItem $localFolder -File | Where-Object { $_.Extension -match "exe|msi|bat|cmd" } | Sort-Object { $_.Name -match "uninstall" } -Descending
    
    if ($files.Count -eq 0) {
        Write-KittingLog "実行可能なファイルが見つかりませんでした。" -Level Warning
        return
    }

    # 発見したファイルを全てログに出力 (デバッグ用)
    Write-KittingLog "【発見したファイル一覧】"
    foreach ($f in $files) { Write-KittingLog " - $($f.Name)" }

    Write-KittingLog "ローカルインストールの実行を開始します (計 $($files.Count) 件)..."
    $current = 0
    foreach ($file in $files) {
        $current++
        Write-Progress -Activity "アプリインストール中" -Status "処理中: $($file.Name)" -PercentComplete ([math]::Round(($current / $files.Count) * 100))
        
        Invoke-WithRetry {
            Write-KittingLog "[$current/$($files.Count)] $($file.Name) を実行中..."
            $workDir = Split-Path $file.FullName
            
            if ($file.Extension -match "bat|cmd") {
                # バッチファイル
                Start-Process cmd.exe -ArgumentList "/c `"$($file.FullName)`"" -WorkingDirectory $workDir -Wait -ErrorAction Stop
            }
            elseif ($file.Extension -eq ".msi") {
                # MSI
                Start-Process msiexec.exe -ArgumentList "/i `"$($file.FullName)`"", "/qn", "/norestart" -WorkingDirectory $workDir -Wait -ErrorAction Stop
            }
            elseif ($file.Name -match "avremover|ees_nt64") {
                # ESET系 (特別なスイッチを試行)
                Start-Process -FilePath $file.FullName -ArgumentList "--quiet", "--accepteula", "/S", "/silent" -WorkingDirectory $workDir -Wait -ErrorAction Stop
            }
            else {
                # 一般的なEXE
                Start-Process -FilePath $file.FullName -ArgumentList "/S", "/silent", "/verysilent", "/qn" -WorkingDirectory $workDir -Wait -ErrorAction Stop
            }
        } -TaskName "$($file.Name)"
    }
    Write-Progress -Activity "アプリインストール" -Completed
}
