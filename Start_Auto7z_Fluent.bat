@echo off
setlocal
cd /d "%~dp0"
if exist "desktop\src-tauri\target\release\auto7z-desktop.exe" (
  start "" "desktop\src-tauri\target\release\auto7z-desktop.exe"
  exit /b 0
)
if exist "%USERPROFILE%\.cargo\bin" set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
where cargo >nul 2>nul
if errorlevel 1 (
  echo Rust stable is required. See desktop\README.md.
  pause
  exit /b 1
)
if not exist "desktop\node_modules" (
  echo Run npm ci in desktop first. See desktop\README.md.
  pause
  exit /b 1
)
cd desktop
call npm.cmd run desktop
if errorlevel 1 pause
