@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment in .venv...
    python -m venv .venv
)

echo [setup] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [setup] Installing remaining requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [setup] Environment setup complete!
endlocal

