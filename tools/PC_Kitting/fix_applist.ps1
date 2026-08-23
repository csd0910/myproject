$path = Join-Path $PSScriptRoot "Set-CorporateStandardEnvironment.ps1"
$lines = Get-Content $path -Encoding UTF8

for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match 'appList = @\("Office2010"') {
        $lines[$i] = '        $appList = @("Office2010", "7-Zip", "AcrobatReader", "Chrome", "VMWare", "Sky_Kikan")'
        Write-Host "Replaced Kikan array"
    }
    if ($lines[$i] -match 'appList = @\("Office365"') {
        $lines[$i] = '        $appList = @("Office365", "7-Zip", "AcrobatReader", "Chrome", "ESET_OA", "Sky_OA")'
        Write-Host "Replaced OA array"
    }
}

$lines | Out-File $path -Encoding UTF8
Write-Host "Success"
