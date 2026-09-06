$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$buildPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) {
    throw 'Crie o ambiente com py -3.12 -m venv .venv e instale requirements-build.txt antes de compilar.'
}
Push-Location -LiteralPath $projectRoot
try {
    & $buildPython -B -m unittest discover -s tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Os testes falharam; compilação cancelada.' }
    # PyInstaller asks before replacing an existing bundle; settings live outside it.
    & $buildPython -m PyInstaller Central.spec
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível gerar Central.exe.' }
    Write-Output (Join-Path $projectRoot 'dist\Central\Central.exe')
} finally {
    Pop-Location
}
