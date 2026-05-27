$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Config = @{
    LogPath = Join-Path $PSScriptRoot "Kitting_Log.txt"
    NASPath = "\\10.85.33.230\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\新しいフォルダー (3)\バッチ・スクリプト\Windowsキッティング用ツール"
    DriveLetter = "Y:"
    Apps = @{
        Chrome = "https://dl.google.com/chrome/install/375.126/chrome_installer.exe"
        SevenZip = "https://www.7-zip.org/a/7z2301-x64.exe"
    }
}
$script:KittingConfig = $Config
