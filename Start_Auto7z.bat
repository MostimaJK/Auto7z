@echo off
setlocal
cd /d "%~dp0"
if exist "desktop\src-tauri\target\release\auto7z.exe" (
  start "" "desktop\src-tauri\target\release\auto7z.exe"
  exit /b 0
)
if exist "desktop\src-tauri\target\debug\auto7z.exe" (
  start "" "desktop\src-tauri\target\debug\auto7z.exe"
  exit /b 0
)
if exist "%USERPROFILE%\.cargo\bin" set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
if not exist "desktop\node_modules" (
  echo Run npm ci in desktop first. See README.md.
  pause
  exit /b 1
)
cd desktop
call npm.cmd run desktop
if errorlevel 1 pause
