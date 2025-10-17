@echo off
echo Welcome! What would you like to run?
echo.
echo 1. Talking Clock
echo 2. Cool Tune
echo.
choice /c 12 /m "Please enter your choice (1 or 2):"

if %errorlevel% equ 1 (
    echo Starting Talking Clock...
    call python comet.py
) else if %errorlevel% equ 2 (
    echo Starting Cool Tune...
    call python star.py
)