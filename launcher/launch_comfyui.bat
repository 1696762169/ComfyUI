@echo off
cd /d "%~dp0.."
title ComfyUI Server
.venv\Scripts\python.exe launcher\launch_comfyui.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Launcher exited with code %ERRORLEVEL%
)
pause
