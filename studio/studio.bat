@echo off
setlocal
set "HERE=%~dp0"
set "PYTHONPATH=%HERE%;%PYTHONPATH%"
set "PYTHONIOENCODING=utf-8"
"%HERE%.venv\Scripts\python.exe" -m studio %*
