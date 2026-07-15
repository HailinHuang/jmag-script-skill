@echo off
setlocal
set "PYTHONPATH=%~dp0src;C:\Program Files\JMAG-Designer25.1;%PYTHONPATH%"
"C:\Program Files\JMAG-Designer25.1\python3.12\python.exe" -m jmag_skill.cli %*
exit /b %ERRORLEVEL%
