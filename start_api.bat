@echo off
setlocal
cd /d "%~dp0"

rem Copy start_api.local.example.bat to start_api.local.bat and add local secrets there.
if exist "%~dp0start_api.local.bat" call "%~dp0start_api.local.bat"

if exist ".venv\Scripts\uvicorn.exe" (
    ".venv\Scripts\uvicorn.exe" src.server.api:app --host 127.0.0.1 --port 8000 --reload
) else (
    uvicorn src.server.api:app --host 127.0.0.1 --port 8000 --reload
)

endlocal