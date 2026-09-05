@echo off
setlocal
cd /d "%~dp0"

rem FastAPI server address used by the Gradio client.
set "TRANSLATION_API_URL=http://127.0.0.1:8000"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m src.client.app
) else (
    python -m src.client.app
)

endlocal