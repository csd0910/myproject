$path = Join-Path $PSScriptRoot "Set-CorporateStandardEnvironment.ps1"
$content = Get-Content $path -Encoding UTF8 -Raw
[System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)
Write-Host "Re-encoded with BOM successfully."
