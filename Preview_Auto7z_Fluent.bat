@echo off
setlocal
cd /d "%~dp0"
if not exist "desktop\src-tauri\target\debug\auto7z-desktop.exe" (
  echo Build the preview first: cd desktop and npm run tauri -- build --debug --no-bundle
  pause
  exit /b 1
)
set "LOCALAPPDATA=%~dp0artifacts\fluent-refinement-profile"
start "" "desktop\src-tauri\target\debug\auto7z-desktop.exe"
