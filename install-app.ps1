$ErrorActionPreference = 'Stop'
$bundle = Join-Path $PSScriptRoot 'dist\Central'
$applicationDirectory = Join-Path $env:LOCALAPPDATA 'Programs\Central'
$settingsDirectory = Join-Path $env:LOCALAPPDATA 'Central'
$desktopDirectory = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopDirectory 'Central.lnk'
if (-not (Test-Path -LiteralPath (Join-Path $bundle 'Central.exe'))) {
    throw 'Gere o aplicativo com build-app.ps1 antes de instalar.'
}
if ((Test-Path -LiteralPath $applicationDirectory) -or (Test-Path -LiteralPath $shortcutPath)) {
    throw 'Já existe uma instalação ou um atalho Central. Os arquivos existentes foram preservados.'
}

New-Item -ItemType Directory -Path $applicationDirectory -Force | Out-Null
Get-ChildItem -LiteralPath $bundle | Copy-Item -Destination $applicationDirectory -Recurse
New-Item -ItemType Directory -Path $settingsDirectory -Force | Out-Null
$savedSettings = Join-Path $settingsDirectory 'config.json'
$projectSettings = Join-Path $PSScriptRoot 'config.json'
if (-not (Test-Path -LiteralPath $savedSettings) -and (Test-Path -LiteralPath $projectSettings)) {
    Copy-Item -LiteralPath $projectSettings -Destination $savedSettings
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $applicationDirectory 'Central.exe'
$shortcut.WorkingDirectory = $applicationDirectory
$shortcut.Description = 'Organizar arquivos em uma pasta central'
$shortcut.IconLocation = $shortcut.TargetPath + ',0'
$shortcut.Save()
[PSCustomObject]@{Application=$shortcut.TargetPath;Shortcut=$shortcutPath;Settings=$savedSettings} | ConvertTo-Json
