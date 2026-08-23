<#
.SYNOPSIS
PC Manufacturer Evidence Extraction Script (Phase 1)
.DESCRIPTION
This script extracts evidence of manufacturer-specific registry and service settings.
#>

# 1. Admin Check and Elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "No Admin rights. Restarting as Administrator..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Base directory
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = (Get-Item $PSCommandPath).DirectoryName }

# Get PC Model Name
$sysInfo = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$modelName = "Unknown_Model"
if ($sysInfo -and $sysInfo.Model) {
    $modelName = $sysInfo.Model -replace '[\\/:*?"<>|]', '_'
    $modelName = $modelName.Trim()
}

$OutDir = Join-Path $scriptDir $modelName
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

# 2. Start Transcript
$LogFile = Join-Path $OutDir "Script_Execution_Log.txt"
Start-Transcript -Path $LogFile -Append -Force

try {
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "Starting Evidence Collection..." -ForegroundColor Cyan
    Write-Host "Model Name : $modelName" -ForegroundColor Cyan
    Write-Host "Output Dir : $OutDir" -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan

    # 00_PC_Info.txt
    Write-Host " 00: Getting PC Info..."
    Get-CimInstance Win32_ComputerSystem -ErrorAction Stop | Select-Object Manufacturer, Model, SystemType | Out-File (Join-Path $OutDir "00_PC_Info.txt")
    Get-CimInstance Win32_BIOS -ErrorAction Stop | Select-Object SMBIOSBIOSVersion, Manufacturer, ReleaseDate | Out-File (Join-Path $OutDir "00_PC_Info.txt") -Append

    # Registry Export Helper
    function Export-RegKey {
        param($Path, $OutFile)
        Write-Host " -> Exporting $OutFile ..."
        $psPath = $Path -replace "^HKEY_CURRENT_USER", "HKCU:" -replace "^HKEY_LOCAL_MACHINE", "HKLM:"
        $destPath = Join-Path $OutDir $OutFile
        
        try {
            if (Test-Path $psPath -ErrorAction Stop) {
                $regArgs = "export `"$Path`" `"$destPath`" /y"
                $process = Start-Process -FilePath "reg.exe" -ArgumentList $regArgs -Wait -NoNewWindow -PassThru
                if ($process.ExitCode -ne 0) {
                    Write-Host "   [Warning] reg.exe exited with code $($process.ExitCode): $Path" -ForegroundColor Red
                }
            } else {
                Write-Host "   [Skip] Key not found: $Path" -ForegroundColor Yellow
                Out-File -FilePath $destPath -InputObject "Key Not Found: $Path" -Encoding UTF8
            }
        } catch {
            Write-Host "   [Error] Failed to check key: $Path" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
    }

    # 01 - 04
    Export-RegKey -Path "HKEY_CURRENT_USER\Control Panel" -OutFile "01_CU_ControlPanel.txt"
    Export-RegKey -Path "HKEY_CURRENT_USER\Software\Microsoft\Windows" -OutFile "02_CU_Windows_Core.txt"
    Export-RegKey -Path "HKEY_CURRENT_USER\SOFTWARE\Policies" -OutFile "03_CU_Policies.txt"
    Export-RegKey -Path "HKEY_LOCAL_MACHINE\SOFTWARE\Policies" -OutFile "04_LM_Policies.txt"

    # 05
    Export-RegKey -Path "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -OutFile "05_LM_Startup_Run.txt"

    # 06
    Export-RegKey -Path "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control" -OutFile "06_LM_System_Control.txt"

    # 07
    Export-RegKey -Path "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services" -OutFile "07_LM_Services_Reg.txt"
    Get-Service | Sort-Object Status -Descending | Format-Table -AutoSize | Out-File (Join-Path $OutDir "07_LM_Services_List.txt") -Encoding UTF8

    # 08
    Write-Host " 08: Getting Manufacturer Apps Registry..."
    $SoftwareKeys = Get-ChildItem "HKLM:\SOFTWARE" -ErrorAction Stop | Where-Object { 
        $_.PSChildName -notmatch "^(Microsoft|Classes|WOW6432Node|Clients|Policies|RegisteredApplications)$" 
    }
    $SoftOutPath = Join-Path $OutDir "08_LM_Manufacturer_Apps.txt"
    Clear-Content $SoftOutPath -ErrorAction SilentlyContinue
    
    $tempReg = Join-Path $OutDir "temp_reg.txt"
    foreach ($key in $SoftwareKeys) {
        $regPath = "HKEY_LOCAL_MACHINE\SOFTWARE\" + $key.PSChildName
        $process = Start-Process -FilePath "reg.exe" -ArgumentList "export `"$regPath`" `"$tempReg`" /y" -Wait -NoNewWindow -PassThru
        if (Test-Path $tempReg) {
            Add-Content -Path $SoftOutPath -Value (Get-Content $tempReg)
            Remove-Item $tempReg -ErrorAction SilentlyContinue
        }
    }

    Write-Host "=============================================" -ForegroundColor Green
    Write-Host "All collection tasks completed successfully." -ForegroundColor Green
    Write-Host "Output Folder: $OutDir" -ForegroundColor Green
    Write-Host "=============================================" -ForegroundColor Green

} catch {
    Write-Host "A fatal error occurred!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Position: $($_.InvocationInfo.PositionMessage)" -ForegroundColor Red
} finally {
    Stop-Transcript
    Write-Host "`nProcess finished. Log saved to $LogFile." -ForegroundColor Cyan
    Read-Host "Press Enter to close this window..."
}
