@echo off
setlocal
set "ECHOES_HOME=%~dp0data"
if not exist "%~dp0items.csv" (
  echo error items.csv not found
  echo.
  echo Put today's items.csv in this folder, then run import.cmd again.
  pause
  exit /b 1
)
"%~dp0echoes.exe" import "%~dp0items.csv"
echo.
pause
