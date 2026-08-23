function Set-BaseSettings {
    param($InputData)
    Write-KittingLog "基盤設定を開始します..."
    
    # ネットワークドライブを全権限で共有するためのレジストリ (重要)
    Set-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLinkedConnections" -Value 1 -Type DWord -Force

    if ($InputData.ComputerName -and ($InputData.ComputerName -ne $env:COMPUTERNAME)) {
        Invoke-WithRetry {
            Rename-Computer -NewName $InputData.ComputerName -Force -ErrorAction Stop
            Write-KittingLog "PC名を $($InputData.ComputerName) に変更しました。"
        } -TaskName "PC名変更"
    }

    # デスクトップアイコン表示 (複数の場所へ適用)
    Invoke-WithRetry {
        $iconKeys = @(
            "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
            "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\ClassicStartMenu"
        )
        foreach ($key in $iconKeys) {
            if (!(Test-Path $key)) { New-Item $key -Force | Out-Null }
            Set-ItemProperty $key -Name "{20D04FE0-3AEA-1069-A2D8-08002B30309D}" -Value 0 -Force # PC
            Set-ItemProperty $key -Name "{5399E694-6D95-4959-BB87-1122357399F3}" -Value 0 -Force # ユーザー
            Set-ItemProperty $key -Name "{21EC2020-3AEA-1069-A2DD-08002B30309D}" -Value 0 -Force # コンパネ
            Set-ItemProperty $key -Name "{645FF040-5081-101B-9F08-00AA002F954E}" -Value 0 -Force # ごみ箱
        }
        Write-KittingLog "デスクトップアイコン表示設定を適用しました。"
    } -TaskName "デスクトップアイコン設定"

    # キーボード106/109固定
    $regKbd = "HKLM:\SYSTEM\CurrentControlSet\Services\i8042prt\Parameters"
    Set-ItemProperty $regKbd -Name "LayerDriver JPN" -Value "kbd106.dll" -Force
    Set-ItemProperty $regKbd -Name "OverrideKeyboardIdentifier" -Value "PCAT_106KEY" -Force
}
