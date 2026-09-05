@echo off
setlocal
cd /d "%~dp0"

rem Copy start_api.local.example.bat to start_api.local.bat and add local secrets there.
if exist "%~dp0start_api.local.bat" call "%~dp0start_api.local.bat"

set "LLM_PROVIDER=groq"
set "LLM_MAX_COMPLETION_TOKENS=1000"
set "LANGSMITH_PROJECT=groq-japanese-dict"
set "LANGSMITH_ENDPOINT=https://api.smith.langchain.com"
if not defined LANGSMITH_API_KEY (
    set "LANGSMITH_TRACING=false"
) else (
    set "LANGSMITH_TRACING=true"
)
set "LANGCHAIN_TRACING_V2=%LANGSMITH_TRACING%"
set "LANGCHAIN_PROJECT=%LANGSMITH_PROJECT%"

if exist ".venv\Scripts\gradio.exe" (
    ".venv\Scripts\gradio.exe" app.py --watch-dirs src
) else (
    gradio app.py --watch-dirs src
)

endlocal