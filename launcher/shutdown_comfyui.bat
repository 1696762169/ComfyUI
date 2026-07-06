@echo off
chcp 65001 >nul
REM ComfyUI 服务器检测工具 — 双击运行
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0shutdown_comfyui.ps1"
