@echo off
title YouTube Downloader GUI

python gui_downloader.py

if %errorlevel% neq 0 (
    echo.
    echo An error occurred while starting the program
    pause
)
