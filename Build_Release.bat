@echo off
setlocal
cd /d "%~dp0"
if not exist ".build-venv\Scripts\python.exe" (
  echo Create .build-venv and install requirements-build.txt first. See README.md.
  pause
  exit /b 1
)
".build-venv\Scripts\python.exe" scripts\build_release.py
if errorlevel 1 pause
