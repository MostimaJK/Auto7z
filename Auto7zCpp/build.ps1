param(
    [Parameter(Mandatory=$true)][string]$QtDirectory,
    [string]$CMake = "cmake"
)
$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$qtRoot = (Resolve-Path -LiteralPath $QtDirectory).Path
$buildRoot = Join-Path $projectRoot "build"
$deployRoot = Join-Path $projectRoot "dist"
& $CMake -S $projectRoot -B $buildRoot -G "Visual Studio 17 2022" -A x64 "-DCMAKE_PREFIX_PATH=$qtRoot"
if ($LASTEXITCODE -ne 0) { throw "CMake configuration failed" }
& $CMake --build $buildRoot --config Release --parallel
if ($LASTEXITCODE -ne 0) { throw "C++ build failed" }
New-Item -ItemType Directory -Force -Path $deployRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $buildRoot "Release/Auto7zCpp.exe") -Destination $deployRoot
& (Join-Path $qtRoot "bin/windeployqt.exe") --release --no-opengl-sw --no-system-d3d-compiler --no-system-dxc-compiler --no-compiler-runtime --skip-plugin-types generic,networkinformation,tls --translations zh_TW --dir $deployRoot (Join-Path $deployRoot "Auto7zCpp.exe")
if ($LASTEXITCODE -ne 0) { throw "Qt deployment failed" }
Copy-Item -LiteralPath (Join-Path $qtRoot "translations/qtbase_zh_TW.qm") -Destination (Join-Path $deployRoot "translations")
$sourceRoot = Split-Path $projectRoot -Parent
foreach ($name in @("7z.exe","7z.dll","Auto7z.ico","LICENSE","THIRD_PARTY_NOTICES.md")) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $deployRoot
}
Copy-Item -LiteralPath (Join-Path $sourceRoot "licenses") -Destination $deployRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $deployRoot
# App-local runtime, from the licensed Visual Studio redistributable directory.
$vswhere = "${env:ProgramFiles(x86)}/Microsoft Visual Studio/Installer/vswhere.exe"
$vsRoot = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$redistRoot = Join-Path $vsRoot "VC/Redist/MSVC"
$crt = Get-ChildItem -LiteralPath $redistRoot -Directory | Where-Object { $_.Name -match '^\d' } | Sort-Object Name -Descending | Select-Object -First 1
if ($null -eq $crt) { throw "MSVC runtime directory not found" }
Copy-Item -Path (Join-Path $crt.FullName "x64/Microsoft.VC143.CRT/*.dll") -Destination $deployRoot
Write-Host "C++ portable build: $deployRoot"
