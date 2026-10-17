$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$desktop = Join-Path $repo 'desktop'
$resources = Join-Path $desktop 'src-tauri/resources'
$python = Join-Path $repo '.build-venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Create .build-venv and install requirements-build.txt first (PyInstaller required).' }
if (Test-Path -LiteralPath "$env:USERPROFILE/.cargo/bin") { $env:PATH = "$env:USERPROFILE/.cargo/bin;" + $env:PATH }
New-Item -ItemType Directory -Force -Path $resources | Out-Null
Push-Location $desktop
try {
    & $python -m PyInstaller --noconfirm --clean --onefile --name auto7z-engine --paths $repo --distpath $resources --workpath "$desktop/.build/work" --specpath "$desktop/.build" "$desktop/backend/bridge.py"
    if ($LASTEXITCODE -ne 0) { throw 'Backend build failed' }
    Copy-Item -LiteralPath "$repo/7z.exe", "$repo/7z.dll", "$repo/LICENSE", "$repo/THIRD_PARTY_NOTICES.md" -Destination $resources
    $licenseTarget = Join-Path $resources 'licenses'
    New-Item -ItemType Directory -Force -Path $licenseTarget | Out-Null
    Copy-Item -LiteralPath "$repo/licenses/7-Zip.txt", "$repo/licenses/Python.txt", "$repo/licenses/GPL-3.0.txt", "$repo/licenses/LGPL-3.0.txt" -Destination $licenseTarget
    & $python "$desktop/scripts/collect_notices.py"
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
    & npm.cmd run tauri -- build
    if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed' }
    & $python "$repo/scripts/build_release.py" --package-only
    if ($LASTEXITCODE -ne 0) { throw 'Distribution packaging failed' }
} finally { Pop-Location }
