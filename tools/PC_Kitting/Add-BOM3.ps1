$path = Join-Path $PSScriptRoot "Inject-Personalization.ps1"
if (Test-Path $path) {
    $content = Get-Content $path -Encoding UTF8 -Raw
    [System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)
    Write-Host "Re-encoded Inject-Personalization.ps1 with BOM successfully."
}
