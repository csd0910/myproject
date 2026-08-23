chcp 65001
set "oldDir=C:\Users\フォーレスト026\MyProject\tools\PC_Kitting\Old\WindowsKittingTool\インストーラー"
set "newDir=C:\Users\フォーレスト026\MyProject\tools\PC_Kitting\Installers"

mkdir "%newDir%\AcrobatReader"
copy "%oldDir%\AcroRdrDC*.exe" "%newDir%\AcrobatReader\" /Y

mkdir "%newDir%\Office365"
copy "%oldDir%\setup.exe" "%newDir%\Office365\" /Y
copy "%oldDir%\configuration*.xml" "%newDir%\Office365\" /Y
copy "%oldDir%\*MS365.bat" "%newDir%\Office365\" /Y

mkdir "%newDir%\Sky"
copy "%oldDir%\SKYSEA*.exe" "%newDir%\Sky\" /Y

mkdir "%newDir%\ESET"
copy "%oldDir%\*ees_nt64.exe" "%newDir%\ESET\" /Y

mkdir "%newDir%\Chrome"
copy "%oldDir%\*chrome*.msi" "%newDir%\Chrome\" /Y

mkdir "%newDir%\7-Zip"
