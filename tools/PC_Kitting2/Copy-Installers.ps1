$oldDir = "C:\Users\フォーレスト026\MyProject\tools\PC_Kitting\Old\WindowsKittingTool\インストーラー"
$newDir = "C:\Users\フォーレスト026\MyProject\tools\PC_Kitting\Installers"

New-Item -ItemType Directory -Path "$newDir\AcrobatReader" -Force | Out-Null
Copy-Item "$oldDir\AcroRdrDC*.exe" "$newDir\AcrobatReader\" -Force

New-Item -ItemType Directory -Path "$newDir\Office365" -Force | Out-Null
Copy-Item "$oldDir\setup.exe" "$newDir\Office365\" -Force
Copy-Item "$oldDir\configuration*.xml" "$newDir\Office365\" -Force
Copy-Item "$oldDir\*MS365.bat" "$newDir\Office365\" -Force

New-Item -ItemType Directory -Path "$newDir\Sky" -Force | Out-Null
Copy-Item "$oldDir\SKYSEA*.exe" "$newDir\Sky\" -Force

New-Item -ItemType Directory -Path "$newDir\ESET" -Force | Out-Null
Copy-Item "$oldDir\*ees_nt64.exe" "$newDir\ESET\" -Force

New-Item -ItemType Directory -Path "$newDir\Chrome" -Force | Out-Null
Copy-Item "$oldDir\*chrome*.msi" "$newDir\Chrome\" -Force

Write-Host "File copy completed successfully."
