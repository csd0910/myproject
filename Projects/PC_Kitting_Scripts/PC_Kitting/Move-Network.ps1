$file = '.\Set-CorporateStandardEnvironment.ps1'
$content = Get-Content $file -Raw
$regex = '(?s)(# Network Settings\r?\nif \(\$setStaticIP -match.*?Add-Check "Wi-Fi Configured" "OK"\r?\n\})'
$match = [regex]::Match($content, $regex)
if ($match.Success) {
    Write-Host 'Match Found!'
    $networkBlock = $match.Value
    $content = $content.Replace($networkBlock, '')
    $insertRegex = '(?s)(# =========================================\r?\n# 3\. Apply System Policies \(HKLM & Global\)\r?\n# =========================================)'
    $content = $content -replace $insertRegex, "$networkBlock`n`n`$1"
    $content | Out-File '.\Set-CorporateStandardEnvironment_bom.ps1' -Encoding UTF8
    Move-Item -Force '.\Set-CorporateStandardEnvironment_bom.ps1' $file
    Write-Host 'Replaced Successfully.'
} else {
    Write-Host 'No Match'
}
