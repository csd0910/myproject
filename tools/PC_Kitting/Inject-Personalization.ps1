$file = '.\Set-CorporateStandardEnvironment.ps1'
$content = Get-Content $file -Raw

$hklmInsert = @"
    # Lock Screen Settings (No Apps & No Sign-In Background)
    if (-not (Test-Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization")) { New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" -Force | Out-Null }
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" -Name "NoLockScreenAppNotifications" -Value 1 -Force
    if (-not (Test-Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System")) { New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -Force | Out-Null }
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -Name "DisableLogonBackgroundImage" -Value 1 -Force
    Add-Check "Lock Screen Policies Configured" "OK"

"@

$content = $content -replace '(?s)(# NTP Server \(コンパネ表記にも反映\))', "$hklmInsert`$1"

$hkcuInsert = @"
    # Screensaver & Wallpaper
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveActive" -Value "1" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveTimeOut" -Value "300" -Force
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "SCRNSAVE.EXE" -Value "C:\Windows\System32\Ribbons.scr" -Force
    
    `$wallpaperPath = Join-Path `$scriptDir "wallpaper.jpg"
    if (Test-Path `$wallpaperPath) {
        Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;
        public class Wallpaper {
            [DllImport("user32.dll", CharSet=CharSet.Auto)]
            public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
        }
"@
        [Wallpaper]::SystemParametersInfo(20, 0, `$wallpaperPath, 3) | Out-Null
    }
    Add-Check "Screensaver & Wallpaper Configured" "OK"

"@

$content = $content -replace '(?s)(# =========================================\r?\n# 4\. Apply User Preferences \(HKCU and Defaults\)\r?\n# =========================================\r?\ntry \{)', "`$1`n$hkcuInsert"

$content | Out-File '.\Set-CorporateStandardEnvironment_bom.ps1' -Encoding UTF8
Move-Item -Force '.\Set-CorporateStandardEnvironment_bom.ps1' $file
Write-Host 'Injections completed successfully.'
