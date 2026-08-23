function Set-Optimization {
    Write-KittingLog "=== 詳細システム設定の個別適用を開始します ==="

    # 1. 視覚効果 (ご提示の5項目のみON、他はすべてOFF)
    Invoke-WithRetry {
        # カスタム設定(3)に変更
        $visual = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        if (!(Test-Path $visual)) { New-Item $visual -Force | Out-Null }
        Set-ItemProperty $visual -Name "VisualFXSetting" -Value 3 -Force

        # 指定の5項目をON (1) に設定
        $desktop = "HKCU:\Control Panel\Desktop"
        Set-ItemProperty $desktop -Name "FontSmoothing" -Value 2 -Force            # フォントの縁を滑らかにする
        Set-ItemProperty $desktop -Name "DragFullWindows" -Value 1 -Force          # ドラッグ中にウィンドウ内容表示
        Set-ItemProperty $desktop -Name "UserPreferencesMask" -Value ([byte[]](0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00)) -Force # 影や基本表示
        
        $expAdv = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        Set-ItemProperty $expAdv -Name "IconsOnly" -Value 0 -Force                 # アイコンの代わりに縮小版を表示(0が縮小版)
        Set-ItemProperty $expAdv -Name "ListviewShadow" -Value 1 -Force            # デスクトップアイコンの名前に影を表示

        Write-KittingLog "視覚効果（厳選5項目のみ有効）を適用しました。"
    } -TaskName "視覚効果カスタム設定"

    # 2. プライバシー・推奨事項・広告設定の徹底オフ
    Invoke-WithRetry {
        # 広告識別子
        $adPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
        if (!(Test-Path $adPath)) { New-Item $adPath -Force | Out-Null }
        Set-ItemProperty $adPath -Name "Enabled" -Value 0 -Force

        # Webサイトへの言語リストアクセス
        Set-ItemProperty "HKCU:\Control Panel\International\User Profile" -Name "HttpAcceptLanguageOptOut" -Value 1 -Force

        # パーソナライズされたオファー・診断データ
        $priv = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy"
        if (!(Test-Path $priv)) { New-Item $priv -Force | Out-Null }
        Set-ItemProperty $priv -Name "TailoredExperiencesWithDiagnosticDataEnabled" -Value 0 -Force

        # 設定アプリ内の推奨事項・オファー
        $cdm = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        Set-ItemProperty $cdm -Name "SubscribedContent-338393Enabled" -Value 0 -Force # 設定での通知
        Set-ItemProperty $cdm -Name "SubscribedContent-353694Enabled" -Value 0 -Force # 推奨事項とオファー
        Set-ItemProperty $cdm -Name "SubscribedContent-353696Enabled" -Value 0 -Force
        Set-ItemProperty $cdm -Name "SystemPaneSuggestionsEnabled" -Value 0 -Force    # スタートメニュー改善

        Write-KittingLog "プライバシー・広告・推奨設定をすべてオフにしました。"
    } -TaskName "プライバシー設定オフ"

    # 3. 電源・ストレージセンサー・マルチタスク
    Invoke-WithRetry {
        powercfg.exe /hibernate off
        powercfg.exe /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 3
        powercfg.exe /setacvalueindex SCHEME_CURRENT SUB_DISK DISKIDLE 0
        powercfg.exe /x -standby-timeout-ac 0; powercfg.exe /x -standby-timeout-dc 0
        
        $ssPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy"
        if (!(Test-Path $ssPath)) { New-Item $ssPath -Force | Out-Null }
        Set-ItemProperty $ssPath -Name "01" -Value 0 -Force

        Set-ItemProperty "HKCU:\Control Panel\Desktop" -Name "WindowArrangementActive" -Value 0 -Force
        $adv = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        Set-ItemProperty $adv -Name "VirtualDesktopTaskbarFilter" -Value 0 -Force
        Set-ItemProperty $adv -Name "VirtualDesktopAltTabFilter" -Value 0 -Force
    } -TaskName "電源・マルチタスク設定"

    # 4. 通知・マウス・リモートデスクトップ・NTP
    Invoke-WithRetry {
        $push = "HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications"
        if (!(Test-Path $push)) { New-Item $push -Force | Out-Null }
        Set-ItemProperty $push -Name "ToastEnabled" -Value 0 -Force
        
        Set-ItemProperty "HKCU:\Control Panel\Desktop" -Name "WheelScrollLines" -Value 1 -Force
        Set-ItemProperty "HKCU:\Control Panel\Desktop" -Name "MouseWheelRouting" -Value 0 -Force
        Set-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0 -Force
        
        Set-Service w32time -StartupType Automatic; Start-Service w32time -ErrorAction SilentlyContinue
        w32tm /config /manualpeerlist:"ntp.nict.jp,0x8" /syncfromflags:manual /reliable:yes /update
    } -TaskName "その他システム設定"

    # BitLocker検証
    try {
        $drive = "C:"; $pcName = $env:COMPUTERNAME
        $keyFile = Join-Path $script:KittingRoot "$($pcName)_BitLockerKey.txt"
        Add-BitLockerKeyProtector -MountPoint $drive -RecoveryPasswordProtector -ErrorAction SilentlyContinue | Out-Null
        $key = (Get-BitLockerVolume -MountPoint $drive).KeyProtector | Where-Object { $_.KeyProtectorType -eq 'RecoveryPassword' }
        if ($key) {
            "PC Name: $pcName`r`nRecovery Key: $($key.RecoveryPassword)" | Out-File -FilePath $keyFile -Encoding UTF8
            Enable-BitLocker -MountPoint $drive -EncryptionMethod XtsAes128 -UsedSpaceOnly -SkipHardwareTest -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
            Disable-BitLocker -MountPoint $drive -ErrorAction SilentlyContinue | Out-Null
            Write-KittingLog "BitLocker回復キーの保存を完了しました。"
        }
    } catch {
        Write-KittingLog "BitLocker設定はスキップされました。" -Level Warning
    }
}
