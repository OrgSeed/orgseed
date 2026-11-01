@echo off
rem Close out: double-click this file. It opens its own console window and runs
rem scripts\fos_close.py unchanged, so the script's own safeguards still apply.
rem No AI is involved. Nothing here sends anything anywhere.
setlocal
cd /d "%~dp0"
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
  where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo Python 3 was not found on this computer. Install it, for example from the Microsoft Store,
  echo then double-click this file again.
  pause
  exit /b 9009
)
%PYCMD% scripts\fos_close.py
set "STATUS=%ERRORLEVEL%"
echo.
pause
exit /b %STATUS%
