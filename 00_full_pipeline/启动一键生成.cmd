@echo off
cd /d "%~dp0"
python workbench.py
if errorlevel 1 pause
