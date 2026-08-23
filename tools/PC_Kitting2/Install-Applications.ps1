<#
.SYNOPSIS
OA Terminal Kitting Tool (Ver.2: Application Installer)
#>

# 1. Admin Check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "No Admin rights. Restarting as Administrator..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = (Get-Item $PSCommandPath).DirectoryName }
$LogsDir = Join-Path $scriptDir "Logs"
$InstallersDir = Join-Path $scriptDir "Installers"

if (-not (Test-Path $InstallersDir)) {
    New-Item -ItemType Directory -Path $InstallersDir | Out-Null
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " OA Terminal Auto Kitting Tool [Ver.2: App Installer]" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$confirm = Read-Host "Start Application Installation? (y/n)"
if ($confirm -notmatch "^y") { exit }

Write-Host "`nStarting Application Installation..." -ForegroundColor Yellow

# =========================================
# 2. Define Applications to Install
# =========================================
# The script expects folders inside 'Installers' matching these names.
# Each folder should contain an 'install.bat' or the installer executable.
$appList = @("Office365", "7-Zip", "AcrobatReader", "Chrome", "ESET", "Sky")

$checklist = @()
function Add-Check {
    param($item, $status)
    $checklist += "[$status] $item"
    Write-Host "[$status] $item"
}

# =========================================
# 3. Process Installations
# =========================================
foreach ($appName in $appList) {
    $appDir = Join-Path $InstallersDir $appName
    
    if (-not (Test-Path $appDir)) {
        Add-Check "Install $appName" "Skip (Folder not found)"
        continue
    }

    Write-Host " -> Installing $appName ..." -ForegroundColor Cyan
    
    # Priority 1: Check for install.bat or setup.bat
    $batFile = Get-ChildItem -Path $appDir -Filter "*.bat" | Select-Object -First 1
    if ($batFile) {
        $process = Start-Process -FilePath $batFile.FullName -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -eq 0) {
            Add-Check "Install $appName" "OK (Batch)"
        } else {
            Add-Check "Install $appName" "NG (ExitCode: $($process.ExitCode))"
        }
        continue
    }

    # Priority 2: Check for MSI
    $msiFile = Get-ChildItem -Path $appDir -Filter "*.msi" | Select-Object -First 1
    if ($msiFile) {
        $process = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$($msiFile.FullName)`" /qn /norestart" -Wait -PassThru
        if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) {
            Add-Check "Install $appName" "OK (MSI Silent)"
        } else {
            Add-Check "Install $appName" "NG (MSI Error: $($process.ExitCode))"
        }
        continue
    }

    # Priority 3: Check for EXE
    $exeFile = Get-ChildItem -Path $appDir -Filter "*.exe" | Select-Object -First 1
    if ($exeFile) {
        $arguments = "/S" # Default
        
        if ($exeFile.Name -match "AcroRdr") {
            $arguments = "/sAll /rs /msi EULA_ACCEPT=YES"
        }
        elseif ($exeFile.Name -match "ees_nt64|avremover") {
            $arguments = "--quiet --accepteula /S /silent"
        }
        elseif ($exeFile.Name -match "setup" -and (Test-Path "$appDir\configuration*.xml")) {
            $xmlFile = Get-ChildItem -Path $appDir -Filter "configuration*.xml" | Select-Object -First 1
            $arguments = "/configure `"$($xmlFile.Name)`""
        }
        elseif ($exeFile.Name -match "SKYSEA") {
            $arguments = "/S /v`"/qn`""
        }

        $process = Start-Process -FilePath $exeFile.FullName -ArgumentList $arguments -Wait -PassThru -WorkingDirectory $appDir
        if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) {
            Add-Check "Install $appName" "OK (EXE Silent)"
        } else {
            Add-Check "Install $appName" "NG (EXE Error: $($process.ExitCode))"
        }
        continue
    }

    Add-Check "Install $appName" "Skip (No installer found in folder)"
}

# =========================================
# 4. Save Checklist
# =========================================
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ChecklistFile = Join-Path $LogsDir "AppInstall_Checklist_$timestamp.txt"
$checklist | Out-File $ChecklistFile -Encoding UTF8

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " App Installation Finished!" -ForegroundColor Green
Write-Host " Checklist: $ChecklistFile" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Green
Read-Host "Press Enter to exit..."
