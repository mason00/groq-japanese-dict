@echo off
setlocal
cd /d "%~dp0"

start "Japanese Dict API" cmd /k call "%~dp0start_api.bat"
start "Japanese Dict React" /D "%~dp0src\react" cmd /k npm run dev -- --host=127.0.0.1

endlocal
